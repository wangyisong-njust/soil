# 时序因果历史记忆模型

该实验为每个重金属单独构建同点历史、近邻历史、近期历史分位数和时空距离加权特征。训练样本只使用更早年份作为历史，2021-2026 测试样本只使用训练期历史记录，避免测试期目标值进入特征。

| target | method | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | causal_history_ml | LightGBM | 0.1665 | 14.8087 | 6.4454 | 42.7762 |
| B | causal_history_ml | XGBoost | 0.3537 | 2.8878 | 1.3097 | 313.6294 |
| C | causal_history_ml | XGBoost | -0.0061 | 36.3278 | 27.8230 | 78.9243 |
| D | causal_history_ml | XGBoost | 0.2329 | 37.6454 | 14.6151 | 31.0102 |
| E | causal_history_ml | XGBoost | 0.4036 | 15.2880 | 7.8042 | 22.8069 |
| F | causal_history_direct | CausalRecentQ90 | -0.0136 | 966.8962 | 217.7579 | 109.9507 |
| G | causal_history_direct | CausalKNN12Median | -0.2336 | 43.9111 | 26.7477 | 40.9456 |
| H | causal_history_ml | XGBoost | 0.1062 | 0.7520 | 0.2124 | 176.8450 |

完整结果见 `tables/causal_history_memory_metrics.csv`；最优结果见 `tables/causal_history_memory_best_metrics.csv`。
