# IchimokuIBtrade
Algorithmic trading

Algorithmic trading using Ichimoku + RSI Indicator

Backtesting uses Backtrader: https://www.backtrader.com/docu/quickstart/quickstart/

With active repository @ backtrader2: https://github.com/backtrader2/backtrader

Feature rich plotting (bokeh): https://github.com/verybadsoldier/backtrader_plotting

Possible trade stategy: Intro: https://school.stockcharts.com/doku.php?id=technical_indicators:ichimoku_cloud Strategy: https://forextraininggroup.com/how-to-use-ichimoku-cloud-strategies-to-trade-forex/

To do:
- Adjust but/sell alg.
- Run optimization(s) --> parameter/starategy comparison
- Implement realitime data + API w Interactive Brokers ((Test built-in backtrader) or better: https://github.com/erdewit/ib_insync.git)
- Backtesting and eval.
- Live test (forex, Equity)

Requirements:
- Matplotlib 3.2.2 (higher triggers bug in BT),
- Pandas,
- backtrader + backtrader2 (latter is maintaned),
- Bokeh (through backtrader_plotting),
- PHP >=3.6,
