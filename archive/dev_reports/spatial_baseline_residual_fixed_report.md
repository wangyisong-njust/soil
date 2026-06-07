# 空间背景值+残差模型修复版

本脚本使用训练期留一空间邻域 IDW 构建训练背景场，测试期只引用训练期样本构建背景场，再对残差进行机器学习回归。背景场中的非有限值用训练期目标中位数兜底，残差模型使用 raw 回归器，并同时评估 0%、25%、50%、100% 残差校正强度，避免过度修正。

| target | method | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | spatial_baseline_residual_fixed | XGBoost_raw_alpha1.00 | 0.1075 | 15.3239 | 8.2600 | 58.3887 |
| B | spatial_baseline_residual_fixed | LightGBM_raw_alpha1.00 | -1.7750 | 5.9838 | 2.8633 | 935.4677 |
| C | spatial_baseline_residual_fixed | XGBoost_raw_alpha0.25 | -0.4929 | 44.2517 | 34.5884 | 102.8278 |
| D | spatial_baseline_residual_fixed | RF_raw_alpha1.00 | -0.0467 | 43.9753 | 26.2750 | 71.5101 |
| E | spatial_baseline_residual_fixed | ExtraTrees_raw_alpha0.50 | -0.4284 | 23.6602 | 12.7486 | 41.2411 |
| F | spatial_baseline_residual_fixed | HistGBR_raw_alpha1.00 | -0.0115 | 965.8965 | 217.4099 | 82.2076 |
| G | spatial_baseline_residual_fixed | ExtraTrees_raw_alpha1.00 | -418.3315 | 809.5940 | 242.6402 | 399.6963 |
| H | spatial_baseline_residual_fixed | RF_raw_alpha1.00 | 0.1246 | 0.7442 | 0.2337 | 236.8974 |

结果表见 `tables/spatial_baseline_residual_fixed_metrics.csv` 和 `tables/spatial_baseline_residual_fixed_best_metrics.csv`；预测明细见 `results/spatial_baseline_residual_fixed_predictions.csv`。
