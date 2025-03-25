from typing import Iterable, Generator, List
import time
import requests
from itertools import chain
import concurrent.futures

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda *args, **kwargs: args[0]

BASE_URL = "api.the-odds-api.com/v4"
PROTOCOL = "https://"


class APIException(RuntimeError):
    def __str__(self):
        return f"('{self.args[0]}', '{self.args[1].json()['message']}')"


class AuthenticationException(APIException):
    pass


class RateLimitException(APIException):
    pass


def handle_faulty_response(response: requests.Response):
    if response.status_code == 401:
        raise AuthenticationException("Failed to authenticate with the API. Is the API key valid?", response)
    elif response.status_code == 429:
        raise RateLimitException("Encountered API rate limit.", response)
    else:
        raise APIException(f"Unknown issue arose while trying to access the API (Status code: {response.status_code}).", response)


def get_sports(key: str) -> List[str]:
    url = f"{BASE_URL}/sports/"
    escaped_url = PROTOCOL + requests.utils.quote(url)
    querystring = {"apiKey": key}

    response = requests.get(escaped_url, params=querystring)
    if not response.ok:
        handle_faulty_response(response)

    # Filter for sports that are likely to have more opportunities
    # You can customize this list based on your preferences
    popular_sports = ["soccer", "basketball", "baseball", "football", "tennis", "hockey"]
    
    sports = []
    for item in response.json():
        # Skip sports that only have outrights (not suitable for arbitrage)
        if item.get("has_outrights") == True and not item.get("active", False):
            continue
            
        # Filter for popular sports to reduce API calls
        if any(pop in item["key"].lower() for pop in popular_sports):
            sports.append(item["key"])
    
    return sports


def get_data(key: str, sport: str, region: str = "eu"):
    url = f"{BASE_URL}/sports/{sport}/odds/"
    escaped_url = PROTOCOL + requests.utils.quote(url)
    querystring = {
        "apiKey": key,
        "regions": region,
        "oddsFormat": "decimal",
        "dateFormat": "unix"
    }

    response = requests.get(escaped_url, params=querystring)
    if not response.ok:
        handle_faulty_response(response)

    return response.json()


def fetch_sport_data(args):
    key, sport, region = args
    try:
        return get_data(key, sport, region)
    except Exception as e:
        print(f"Error fetching data for {sport}: {str(e)}")
        return []


def process_data(matches: Iterable, include_started_matches: bool = True, cutoff: float = 0) -> Generator[dict, None, None]:
    """Extracts all matches and finds all viable bookmaker combinations for arbitrage."""
    matches = tqdm(matches, desc="Checking all matches", leave=False, unit=" matches")
    
    for match in matches:
        start_time = int(match["commence_time"])
        if not include_started_matches and start_time < time.time():
            continue
            
        match_name = f"{match['home_team']} v. {match['away_team']}"
        time_to_start = (start_time - time.time())/3600
        league = match["sport_key"]
        
        # Get all bookmakers' odds for each outcome
        outcomes_data = {}
        
        for bookmaker in match["bookmakers"]:
            bookie_name = bookmaker["title"]
            
            # Focus on the first market (moneyline)
            if not bookmaker["markets"]:
                continue
                
            market = bookmaker["markets"][0]  # Moneyline market
            
            for outcome in market["outcomes"]:
                outcome_name = outcome["name"]
                odd = outcome["price"]
                
                if outcome_name not in outcomes_data:
                    outcomes_data[outcome_name] = []
                
                outcomes_data[outcome_name].append((bookie_name, odd))
        
        # Sort each outcome's odds from best to worst
        for outcome_name in outcomes_data:
            outcomes_data[outcome_name].sort(key=lambda x: x[1], reverse=True)
        
        # Skip if we don't have enough outcomes
        outcome_names = list(outcomes_data.keys())
        if len(outcome_names) < 2:
            continue  # Need at least 2 outcomes for an arbitrage opportunity
        
        # Quick check: Is arbitrage possible with the best odds?
        best_odds = {name: outcomes_data[name][0][1] for name in outcome_names if outcomes_data[name]}
        total_implied_odds = sum(1/odd for odd in best_odds.values())
        
        # Skip if no arbitrage is possible even with best odds
        if total_implied_odds >= 1:
            continue
            
        # If we have more than 3 outcomes, limit combinations to improve performance
        if len(outcome_names) > 3:
            # Use only top 2 bookmakers for each outcome to limit combinations
            for outcome in outcomes_data:
                if len(outcomes_data[outcome]) > 2:
                    outcomes_data[outcome] = outcomes_data[outcome][:2]
        
        # Generate viable bookmaker combinations
        from itertools import product
        
        # Generate possible combinations of bookmakers
        bookmaker_options = [outcomes_data[outcome] for outcome in outcome_names]
        
        for combination in product(*bookmaker_options):
            # Create a dict of best odds for this combination
            best_odds = {outcome_names[i]: combination[i] for i in range(len(outcome_names))}
            
            # Calculate implied odds
            total_implied_odds = sum(1/odd[1] for odd in best_odds.values())
            
            # Check if this is an arbitrage opportunity that meets our cutoff
            if total_implied_odds < 1 and total_implied_odds > 0 and (1 - total_implied_odds) >= cutoff:
                yield {
                    "match_name": match_name,
                    "match_start_time": start_time,
                    "hours_to_start": time_to_start,
                    "league": league,
                    "best_outcome_odds": best_odds,
                    "total_implied_odds": total_implied_odds,
                }


def get_arbitrage_opportunities(key: str, region: str, cutoff: float = 0, selected_sports=None):
    """
    Find arbitrage opportunities across sports betting markets.
    
    Args:
        key (str): API key for The Odds API
        region (str): Region code (e.g., "us", "eu", "uk", "au")
        cutoff (float): Minimum profit margin (0.01 = 1%)
        selected_sports (list, optional): List of sports to filter results. If None, all available sports are used.
    
    Returns:
        list: List of arbitrage opportunities that meet the criteria
    """
    # Get available sports
    if selected_sports is None or len(selected_sports) == 0:
        sports = get_sports(key)
    else:
        sports = selected_sports
    
    # Fetch data for each sport in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        args = [(key, sport, region) for sport in sports]
        results = list(executor.map(fetch_sport_data, args))
    
    # Flatten the list of match data
    data = chain.from_iterable(results)
    
    # Filter out any message objects
    data = filter(lambda x: isinstance(x, dict) and "message" not in x, data)
    
    # Process the data with our cutoff incorporated directly
    arbitrage_opportunities = process_data(data, cutoff=cutoff)
    
    # Convert to list for immediate results
    return list(arbitrage_opportunities)