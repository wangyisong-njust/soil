# 预设近三年中位数基线

该基线不进行超参数搜索，只使用训练期最后三年的目标变量中位数作为预测值。它用于在机器学习模型外推不稳定时提供预注册的分布中心参照，不使用 2022-2026 测试期目标值调参。

| target | model | recent_start_year | recent_median | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | Recent3YearMedian | 2019 | 14.2000 | -0.0187 | 19.3846 | 7.6014 | 55.1361 |
| B | Recent3YearMedian | 2019 | 0.4100 | -0.0368 | 2.0941 | 0.7845 | 217.6797 |
| C | Recent3YearMedian | 2019 | 51.5000 | -0.0650 | 35.1087 | 26.5338 | 79.0975 |
| D | Recent3YearMedian | 2019 | 33.1700 | -0.0476 | 51.5831 | 18.6034 | 27.5997 |
| E | Recent3YearMedian | 2019 | 30.9000 | -0.0910 | 25.4181 | 11.2089 | 24.4985 |
| F | Recent3YearMedian | 2019 | 44.6500 | -0.7359 | 105.9852 | 69.0059 | 50.0554 |
| G | Recent3YearMedian | 2019 | 80.4000 | -0.1039 | 28.8291 | 20.0322 | 39.4076 |
| H | Recent3YearMedian | 2019 | 0.0940 | -0.0346 | 0.2398 | 0.1116 | 172.4102 |

输出文件：`tables/predefined_recent_median_baseline_metrics.csv`、`results/predefined_recent_median_baseline_predictions.csv`。
