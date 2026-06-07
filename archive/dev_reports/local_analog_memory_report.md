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
| literature_2019_2020 | G | local_analog_memory_ml | NGBoost | 815 | 100 | 64 | 0.0231 | 123.1530 | 50.9128 | 40.3167 |
| literature_2019_2020 | H | local_analog_direct | AnalogIDW | 815 | 100 | 19 | 0.4075 | 0.2748 | 0.1075 | 78.0509 |
| temporal_2021_2026 | A | local_analog_memory_ml | XGBoost | 915 | 57 | 64 | 0.1706 | 14.7722 | 6.8190 | 45.3031 |
| temporal_2021_2026 | B | local_analog_memory_ml | ElasticNet | 915 | 57 | 64 | 0.3302 | 2.9398 | 1.3012 | 352.9357 |
| temporal_2021_2026 | C | local_analog_direct | AnalogMedian | 915 | 57 | 19 | -0.0674 | 37.4179 | 26.9844 | 74.5480 |
| temporal_2021_2026 | D | local_analog_memory_ml | ElasticNet | 915 | 57 | 64 | 0.2395 | 37.4842 | 15.7804 | 36.3759 |
| temporal_2021_2026 | E | local_analog_memory_ml | NGBoost | 915 | 57 | 64 | 0.5257 | 13.6340 | 7.3912 | 24.9302 |
| temporal_2021_2026 | F | local_analog_memory_ml | LightGBM | 915 | 57 | 64 | -0.0251 | 972.3625 | 208.2510 | 59.5484 |
| temporal_2021_2026 | G | local_analog_direct | AnalogMedian | 915 | 57 | 19 | -0.2343 | 43.9244 | 26.7741 | 40.9850 |
| temporal_2021_2026 | H | local_analog_memory_ml | HistGBR | 915 | 57 | 64 | 0.1898 | 0.7160 | 0.1855 | 149.9495 |

完整结果见 `tables/local_analog_memory_metrics.csv`、`tables/local_analog_memory_best_metrics.csv` 和 `results/local_analog_memory_predictions.csv`。
