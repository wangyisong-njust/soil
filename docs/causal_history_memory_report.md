# 时序因果历史记忆模型

该实验为每个重金属单独构建同点历史、近邻历史、近期历史分位数和时空距离加权特征。训练样本只使用更早年份作为历史，2022-2026 测试样本只使用训练期历史记录，避免测试期目标值进入特征。

| target | method | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | causal_history_ml | ElasticNet | 0.1732 | 17.4633 | 7.5871 | 56.1713 |
| B | causal_history_ml | ExtraTrees | 0.3078 | 1.7110 | 0.9201 | 391.6686 |
| C | causal_history_ml | XGBoost | 0.0535 | 33.0977 | 23.0221 | 63.4342 |
| D | causal_history_ml | HistGBR | 0.3438 | 40.8255 | 15.8921 | 27.9342 |
| E | causal_history_ml | LightGBM | 0.3881 | 19.0350 | 9.9696 | 23.8859 |
| F | causal_history_ml | LightGBM | 0.3414 | 65.2850 | 39.7116 | 30.9393 |
| G | causal_history_direct | CausalKNN12Median | -0.0492 | 28.1052 | 18.5758 | 36.6344 |
| H | causal_history_direct | CausalRecentQ90 | -0.0475 | 0.2413 | 0.1696 | 408.6415 |

完整结果见 `tables/causal_history_memory_metrics.csv`；最优结果见 `tables/causal_history_memory_best_metrics.csv`。
