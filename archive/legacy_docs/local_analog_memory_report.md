# 局部历史污染记忆模型

输入数据：`data/processed/soil_heavy_metals_external_osm.csv`。该方法从训练期历史样点中为每个预测点提取邻域目标变量的 IDW、均值、中位数、上分位数、最大值、同点历史值、近年最大值和高污染邻域计数等特征。

创新点是把土壤重金属的局部污染记忆和空间类比机制显式加入模型。测试期特征只引用训练期目标值，不使用测试期真实浓度。

| protocol | target | method | model | n_train | n_test | n_features | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| literature_2019_2020 | A | local_analog_memory_ml | XGBoost | 815 | 100 | 64 | 0.1216 | 13.1010 | 7.1982 | 47.2743 |
| literature_2019_2020 | B | local_analog_memory_ml | ElasticNet | 815 | 100 | 64 | 0.0698 | 2.0966 | 1.1105 | 314.2431 |
| literature_2019_2020 | C | local_analog_memory_ml | XGBoost | 815 | 100 | 64 | 0.0266 | 51.7006 | 24.3997 | 38.0820 |
| literature_2019_2020 | D | local_analog_memory_ml | CatBoost | 815 | 100 | 64 | 0.0934 | 54.8100 | 23.2988 | 57.6894 |
| literature_2019_2020 | E | local_analog_memory_ml | CatBoost | 815 | 100 | 64 | 0.1032 | 10.6319 | 7.3420 | 27.5097 |
| literature_2019_2020 | F | local_analog_memory_ml | CatBoost | 815 | 100 | 64 | 0.1502 | 79.1203 | 36.8550 | 58.4267 |
| literature_2019_2020 | G | local_analog_memory_ml | NGBoost | 815 | 100 | 64 | 0.0179 | 123.4796 | 51.4875 | 41.8866 |
| literature_2019_2020 | H | local_analog_direct | AnalogIDW | 815 | 100 | 19 | 0.4075 | 0.2748 | 0.1075 | 78.0509 |
| temporal_2022_2026 | A | local_analog_memory_ml | XGBoost | 938 | 34 | 64 | 0.2289 | 16.8646 | 7.3268 | 50.7633 |
| temporal_2022_2026 | B | local_analog_memory_ml | LightGBM | 938 | 34 | 64 | 0.3131 | 1.7045 | 0.8214 | 295.9347 |
| temporal_2022_2026 | C | local_analog_memory_ml | ElasticNet | 938 | 34 | 64 | 0.0671 | 32.8578 | 22.7825 | 64.3489 |
| temporal_2022_2026 | D | local_analog_memory_ml | LightGBM | 938 | 34 | 64 | 0.2880 | 42.5268 | 16.2644 | 29.3304 |
| temporal_2022_2026 | E | local_analog_memory_ml | NGBoost | 938 | 34 | 64 | 0.5368 | 16.5618 | 9.4242 | 27.8009 |
| temporal_2022_2026 | F | local_analog_memory_ml | LightGBM | 938 | 34 | 64 | 0.2620 | 69.1060 | 46.3802 | 38.5200 |
| temporal_2022_2026 | G | local_analog_memory_ml | NGBoost | 938 | 34 | 64 | 0.1003 | 26.0265 | 19.3498 | 38.9040 |
| temporal_2022_2026 | H | local_analog_memory_ml | ElasticNet | 938 | 34 | 64 | 0.0335 | 0.2318 | 0.1115 | 176.4727 |

完整结果见 `tables/local_analog_memory_metrics.csv`、`tables/local_analog_memory_best_metrics.csv` 和 `results/local_analog_memory_predictions.csv`。
