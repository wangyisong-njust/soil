# 空间分块交叉验证

本实验采用 KMeans 空间聚类形成空间块，并逐块留出作为测试集。训练时不使用留出空间块的目标值；目标变量空间滞后特征也只由训练空间块计算。该验证用于评估模型跨区域泛化能力，不替代 2021-2026 时间外推主验证。

| target | model | n_folds | n_test_total | r2 | fold_median_r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | HistGBR | 5 | 972 | 0.0856 | -0.0272 | 20.1171 | 6.3442 | 47.0140 |
| B | ExtraTrees | 5 | 972 | 0.0104 | -0.0184 | 4.7762 | 1.2089 | 244.9197 |
| C | RF | 5 | 972 | -0.0355 | -0.0381 | 35.2828 | 21.7873 | 58.0672 |
| D | RF | 5 | 972 | 0.0330 | -0.0506 | 49.6610 | 17.4485 | 40.7362 |
| E | ExtraTrees | 5 | 972 | -0.0279 | -0.0664 | 29.2351 | 7.9064 | 23.5654 |
| F | ExtraTrees | 5 | 972 | 0.0046 | -0.0005 | 279.4055 | 53.4584 | 74.9310 |
| G | ExtraTrees | 5 | 972 | -0.0014 | -0.0341 | 352.5066 | 65.5821 | 49.8668 |
| H | ElasticNet | 5 | 972 | -0.0913 | -0.2666 | 0.3906 | 0.1302 | 95.2595 |

空间分块验证下平均 R2=-0.0028，中位 R2=0.0016，4/8 个目标为正。

完整逐折结果见 `tables/spatial_block_cv_metrics.csv`；汇总结果见 `tables/spatial_block_cv_pooled_metrics.csv` 和 `tables/spatial_block_cv_best_metrics.csv`；预测明细见 `results/spatial_block_cv_predictions.csv`；图件见 `figures/spatial_block_cv/spatial_block_cv_best_r2.png`。
