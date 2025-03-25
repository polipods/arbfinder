# Sports Arbitrage Finder

A desktop application to automatically find arbitrage betting opportunities across different sportsbooks.


## What is Arbitrage Betting?

Arbitrage betting (also known as "arbing" or "sure betting") is a strategy where you place bets on all possible outcomes of an event at odds that guarantee a profit regardless of the result. This happens when bookmakers disagree on the odds of an event, creating an opportunity for guaranteed returns.

## Features

- **Automatic Arbitrage Detection**: Scan multiple sports and bookmakers to find profitable arbitrage opportunities
- **Sports Filtering**: Select specific sports to narrow your search
- **Profit Margin Calculation**: Set a minimum profit threshold for opportunities
- **Bankroll Management**: Calculate optimal stake distribution across different outcomes
- **Detailed Results**: View opportunities in both table and text formats
- **Data Export**: Export results to CSV or JSON formats for further analysis

## Getting Started

#### Option 1: Using the executable (Windows)

1. Download the repository

2. Run Arbitrage FInder.exe

3. Input in your API Key from the Odds API https://the-odds-api.com/account/
  - You need to sign up to get a free key
  - For acccess to more data you may need to pay for a subscription

#### Option 2: Build the exe from source

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/sports-arbitrage-finder.git
   cd sports-arbitrage-finder
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the main file:
   ```
   python main.py
   ```

4. Continue from step 2 in option 1 (the exe will be in a dist folder)

## Usage

1. **API Key**: Enter your API key from The Odds API
2. **Load Sports**: Click "Load Sports" to retrieve available sports
3. **Filter Sports**: Select the sports you want to include in your search
4. **Region Selection**: Choose your betting region (us, eu, uk, au)
5. **Profit Margin**: Set the minimum profit percentage you're looking for
6. **Bankroll**: Enter your bankroll amount to calculate bet allocations
7. **Find Opportunities**: Click to scan for arbitrage opportunities
8. **Results**: View results in the table or text tab
9. **Export**: Save your findings as CSV or JSON for record keeping

### Tips for Successful Arbitrage Betting

- **Act Quickly**: Arbitrage opportunities can disappear within minutes
- **Consider Bookmaker Limits**: Some bookmakers limit accounts that consistently win
- **Watch for Terms & Conditions**: Be aware of specific bookmaker rules
- **Mind the Fees**: Transaction fees can eat into profits
- **Start Small**: Begin with a modest bankroll until you're comfortable with the process

## API Usage Notes

The application uses [The Odds API](https://the-odds-api.com/) which has usage limits:
- Free tier: 500 requests per month
- Paid tiers available for more frequent usage

The app is designed to be efficient with API calls by:
- Only fetching data for selected sports
- Using multi-threading to process data faster
- Allowing you to export findings to analyze offline

## Troubleshooting

- **No Sports Loading**: Verify your API key and internet connection
- **No Opportunities Found**: Try expanding your sport selection or lowering your profit margin
- **Application Errors**: Check the console output for error messages

## Development

### Project Structure

```
sports-arbitrage-finder/
├── main.py             # Application entry point
├── requirements.txt    # Python dependencies
├── src/
│   ├── gui.py          # PyQt5 GUI implementation
│   ├── logic.py        # Arbitrage detection logic
│   └── utils.py        # Helper functions
├── tests/              # Unit tests
└── docs/               # Documentation
```

