# 空间背景值+残差模型修复版

本脚本使用训练期留一空间邻域 IDW 构建训练背景场，测试期只引用训练期样本构建背景场，再对残差进行机器学习回归。背景场中的非有限值用训练期目标中位数兜底，残差模型使用 raw 回归器，并同时评估 0%、25%、50%、100% 残差校正强度，避免过度修正。

| target | method | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | spatial_baseline_residual_fixed | XGBoost_raw_alpha1.00 | 0.3815 | 15.1038 | 6.9030 | 49.6646 |
| B | spatial_baseline_residual_fixed | XGBoost_raw_alpha1.00 | -1.9323 | 3.5217 | 1.8420 | 667.1159 |
| C | spatial_baseline_residual_fixed | HistGBR_raw_alpha0.50 | -0.0815 | 35.3784 | 28.8521 | 86.5056 |
| D | spatial_baseline_residual_fixed | RF_raw_alpha1.00 | 0.2013 | 45.0409 | 21.1519 | 45.6711 |
| E | spatial_baseline_residual_fixed | ExtraTrees_raw_alpha1.00 | 0.2031 | 21.7239 | 12.4338 | 40.7701 |
| F | spatial_baseline_residual_fixed | IDW_background_alpha0 | -0.4591 | 97.1682 | 70.2285 | 68.5378 |
| G | spatial_baseline_residual_fixed | HistGBR_raw_alpha0.50 | -5.4581 | 69.7299 | 62.3898 | 87.0853 |
| H | spatial_baseline_residual_fixed | XGBoost_raw_alpha1.00 | -0.0816 | 0.2452 | 0.1460 | 300.3848 |

结果表见 `tables/spatial_baseline_residual_fixed_metrics.csv` 和 `tables/spatial_baseline_residual_fixed_best_metrics.csv`；预测明细见 `results/spatial_baseline_residual_fixed_predictions.csv`。
