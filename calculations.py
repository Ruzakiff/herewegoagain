from decimal import Decimal, ROUND_HALF_UP
from scipy.optimize import fsolve

def calculate_implied_probability(american_odds):
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return -american_odds / (-american_odds + 100)

def calculate_no_vig_fair_odds(probabilities):
    total_probability = sum(probabilities)
    return [p / total_probability for p in probabilities]

def calculate_expected_value(stake, probability, payout):
    return (probability * payout) - stake

def analyze_arbitrage(bookmaker_odds):
    total_inverse_probability = sum(1 / Decimal(odds) for odds in bookmaker_odds)
    arbitrage_opportunity = total_inverse_probability < 1
    profit_percentage = (1 - total_inverse_probability) * 100 if arbitrage_opportunity else 0
    return arbitrage_opportunity, profit_percentage

def power_devig(price1, price2):
    price1 = Decimal(str(price1))
    price2 = Decimal(str(price2))
    
    def f(k):
        ri1 = 1 / price1
        ri2 = 1 / price2
        return float((ri1**(Decimal('1')/Decimal(str(k[0]))) + ri2**(Decimal('1')/Decimal(str(k[0]))) - 1))

    k_initial_guess = [1]
    k_solution = fsolve(f, k_initial_guess)

    pi1 = (1 / price1)**(Decimal('1')/Decimal(str(k_solution[0])))
    pi2 = (1 / price2)**(Decimal('1')/Decimal(str(k_solution[0])))
    
    return float(1 / pi1), float(1 / pi2)

def mult_devig(price1, price2):
    price1 = Decimal(str(price1))
    price2 = Decimal(str(price2))
    compoverimplied = 1 / price1
    compunderimplied = 1 / price2
    actualoverdecimal = compoverimplied / (compoverimplied + compunderimplied)
    actualunderdecimal = compunderimplied / (compoverimplied + compunderimplied)
    return float(1 / actualoverdecimal), float(1 / actualunderdecimal)

def additive_devig(price1, price2):
    compoverimplied = 1 / price1
    compunderimplied = 1 / price2
    total_probability = compoverimplied + compunderimplied
    actualoverdecimal = 1 / (compoverimplied / total_probability)
    actualunderdecimal = 1 / (compunderimplied / total_probability)
    return actualoverdecimal, actualunderdecimal

def calculate_ev_difference(sharp_odds, base_odds):
    sharp_odds = Decimal(str(sharp_odds))
    base_odds = Decimal(str(base_odds))
    sharp_prob = Decimal('1') / sharp_odds
    base_prob = Decimal('1') / base_odds
    ev = ((base_odds / sharp_odds - 1) * sharp_prob * 100).quantize(Decimal('0.01'))
    return float(ev)  # Convert to float and return as percentage
def american_to_decimal(american_odds):
    american_odds = Decimal(str(american_odds))
    if american_odds >= 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1

def decimal_to_american(decimal_odds):
    decimal_odds = Decimal(str(decimal_odds))
    if decimal_odds >= 2:
        return ((decimal_odds - 1) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    else:
        return (-100 / (decimal_odds - 1)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)

async def analyze_event(event, odds):
    results = {
        "event": f"{event['home_team']} vs {event['away_team']}",
        "bookmaker_data": [],
        "arbitrage_opportunities": [],
        "value_bets": []
    }

    for bookmaker in odds.get('bookmakers', []):
        bookmaker_data = {
            "name": bookmaker['title'],
            "markets": {}
        }

        for market in bookmaker.get('markets', []):
            market_data = []
            probabilities = []

            for outcome in market.get('outcomes', []):
                american_odds = outcome['price']
                implied_prob = calculate_implied_probability(american_odds)
                probabilities.append(implied_prob)
                market_data.append({
                    "outcome": outcome['name'],
                    "american_odds": american_odds,
                    "implied_probability": implied_prob
                })

            fair_probabilities = calculate_no_vig_fair_odds(probabilities)
            for i, outcome in enumerate(market_data):
                outcome["fair_probability"] = fair_probabilities[i]
                outcome["expected_value"] = calculate_expected_value(100, fair_probabilities[i], outcome["american_odds"])

            bookmaker_data["markets"][market['key']] = market_data

        results["bookmaker_data"].append(bookmaker_data)

    # Analyze arbitrage opportunities across bookmakers
    for market_key in results["bookmaker_data"][0]["markets"].keys():
        best_odds = {}
        for bookmaker in results["bookmaker_data"]:
            for outcome in bookmaker["markets"][market_key]:
                if outcome["outcome"] not in best_odds or outcome["american_odds"] > best_odds[outcome["outcome"]]:
                    best_odds[outcome["outcome"]] = outcome["american_odds"]
        
        arb_opportunity, profit_percentage = analyze_arbitrage(best_odds.values())
        if arb_opportunity:
            results["arbitrage_opportunities"].append({
                "market": market_key,
                "profit_percentage": profit_percentage,
                "best_odds": best_odds
            })

    # Identify value bets
    for bookmaker in results["bookmaker_data"]:
        for market_key, market_data in bookmaker["markets"].items():
            for outcome in market_data:
                if outcome["expected_value"] > 0:
                    results["value_bets"].append({
                        "bookmaker": bookmaker["name"],
                        "market": market_key,
                        "outcome": outcome["outcome"],
                        "american_odds": outcome["american_odds"],
                        "expected_value": outcome["expected_value"]
                    })

    return results
