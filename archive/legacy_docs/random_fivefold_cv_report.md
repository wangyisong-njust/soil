# 随机五折交叉验证

本实验使用随机五折交叉验证评价模型的一般拟合能力。每个折内目标空间滞后特征只由训练折目标值计算，避免验证折目标泄漏。

| target | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- |
| A | RF | 0.0688 | 20.3011 | 5.8730 | 38.3741 |
| B | ExtraTrees | 0.0270 | 4.7359 | 1.0805 | 165.1375 |
| C | XGBoost | 0.0637 | 33.5508 | 19.6204 | 46.3883 |
| D | XGBoost | 0.0721 | 48.6468 | 16.9113 | 39.1666 |
| E | XGBoost | 0.0251 | 28.4705 | 7.0984 | 20.0426 |
| F | LightGBM | 0.0493 | 273.0618 | 50.6997 | 64.1729 |
| G | ExtraTrees | 0.0013 | 352.0374 | 63.0073 | 47.3392 |
| H | XGBoost | 0.1752 | 0.3396 | 0.1012 | 84.1835 |

结果表见 `tables/random_fivefold_cv_metrics.csv` 和 `tables/random_fivefold_cv_best_metrics.csv`；预测明细见 `results/random_fivefold_cv_predictions.csv`；图件见 `figures/validation_strategy/random_fivefold_best_r2.png`。
