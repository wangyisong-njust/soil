# 预设近三年中位数基线

该基线不进行超参数搜索，只使用训练期最后三年的目标变量中位数作为预测值。它用于在机器学习模型外推不稳定时提供预注册的分布中心参照，不使用 2021-2026 测试期目标值调参。

| target | model | recent_start_year | recent_median | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | Recent3YearMedian | 2018 | 13.3000 | -0.0577 | 16.6823 | 7.2159 | 44.3867 |
| B | Recent3YearMedian | 2018 | 0.3800 | -0.0850 | 3.7417 | 1.3429 | 172.7127 |
| C | Recent3YearMedian | 2018 | 57.8600 | -0.1318 | 38.5293 | 29.5429 | 89.9071 |
| D | Recent3YearMedian | 2018 | 31.8000 | -0.0626 | 44.3069 | 17.3280 | 32.3223 |
| E | Recent3YearMedian | 2018 | 31.4500 | -0.0326 | 20.1169 | 8.9518 | 24.2337 |
| F | Recent3YearMedian | 2018 | 37.3000 | -0.0524 | 985.2628 | 222.3341 | 59.2772 |
| G | Recent3YearMedian | 2018 | 80.0000 | -0.0014 | 39.5631 | 23.4134 | 35.5006 |
| H | Recent3YearMedian | 2018 | 0.1000 | -0.0242 | 0.8050 | 0.1892 | 136.0621 |

输出文件：`tables/predefined_recent_median_baseline_metrics.csv`、`results/predefined_recent_median_baseline_predictions.csv`。
