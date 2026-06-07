# 数据清洗策略对照

本报告比较不同数据清洗策略在时间外推验证中的表现。清洗规则只包括格式纠错、重复观测聚合、驱动因子缺失填补、驱动因子温和截尾，以及可选的目标变量极端值剔除。

## 策略汇总

| strategy | n_samples | mean_best_r2 | median_best_r2 | min_best_r2 | max_best_r2 | mean_best_rmse |
| --- | --- | --- | --- | --- | --- | --- |
| basic | 977 | 0.0407 | 0.1359 | -0.8992 | 0.4602 | 141.8291 |
| quality | 972 | 0.0179 | 0.1609 | -1.1915 | 0.4791 | 142.2460 |
| quality_target_mild | 814 | -0.1528 | 0.0442 | -0.9803 | 0.3638 | 16.3740 |
| quality_target_strict | 782 | -0.1811 | 0.0337 | -1.1783 | 0.2433 | 16.3992 |

## 各目标最佳结果

| strategy | target | protocol | model | n_samples | n_train | n_test | r2 | r2_log1p | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| basic | A | temporal | LightGBM | 977 | 920 | 57 | 0.1588 | 0.0825 | 14.8776 | 7.7935 | 52.6726 |
| basic | B | temporal | WeightedEnsemble | 977 | 920 | 57 | 0.4602 | 0.3213 | 2.6393 | 1.2635 | 334.5636 |
| basic | C | temporal | RF | 977 | 920 | 57 | -0.0572 | -0.3661 | 37.2380 | 27.3792 | 76.3655 |
| basic | D | temporal | PLSR | 977 | 920 | 57 | 0.1580 | 0.2135 | 39.4404 | 16.3901 | 37.3152 |
| basic | E | temporal | NGBoost | 977 | 920 | 57 | 0.4112 | 0.1270 | 15.1907 | 8.7582 | 27.2650 |
| basic | F | temporal | LightGBM | 977 | 920 | 57 | -0.0201 | -0.2515 | 970.0137 | 209.7689 | 59.2378 |
| basic | G | temporal | CatBoost | 977 | 920 | 57 | -0.8992 | -0.5286 | 54.4841 | 34.6872 | 52.6562 |
| basic | H | temporal | NGBoost | 977 | 920 | 57 | 0.1138 | 0.1377 | 0.7488 | 0.2220 | 190.7366 |
| quality | A | temporal | LightGBM | 972 | 915 | 57 | 0.2645 | 0.1503 | 13.9111 | 7.5281 | 51.1887 |
| quality | B | temporal | WeightedEnsemble | 972 | 915 | 57 | 0.4791 | 0.3504 | 2.5924 | 1.2700 | 349.1961 |
| quality | C | temporal | RF | 972 | 915 | 57 | -0.0729 | -0.3880 | 37.5138 | 27.7282 | 77.1714 |
| quality | D | temporal | PLSR | 972 | 915 | 57 | 0.1770 | 0.2327 | 38.9926 | 16.3142 | 37.3062 |
| quality | E | temporal | PLSR | 972 | 915 | 57 | 0.3617 | 0.2120 | 15.8161 | 8.4350 | 26.3411 |
| quality | F | temporal | HistGBR | 972 | 915 | 57 | -0.0198 | -0.3255 | 969.8785 | 211.0199 | 60.6308 |
| quality | G | temporal | CatBoost | 972 | 915 | 57 | -1.1915 | -0.5961 | 58.5276 | 35.7815 | 53.6503 |
| quality | H | temporal | NGBoost | 972 | 915 | 57 | 0.1448 | 0.2121 | 0.7356 | 0.2079 | 167.4011 |
| quality_target_mild | A | temporal | ElasticNet | 814 | 772 | 42 | 0.0016 | -0.0865 | 4.8729 | 3.9419 | 46.4528 |
| quality_target_mild | B | temporal | CatBoost | 814 | 772 | 42 | 0.2158 | 0.1706 | 0.4597 | 0.3144 | 196.8485 |
| quality_target_mild | C | temporal | RF | 814 | 772 | 42 | -0.9803 | -1.3739 | 24.9764 | 22.6999 | 83.4221 |
| quality_target_mild | D | temporal | ExtraTrees | 814 | 772 | 42 | 0.1518 | 0.2007 | 13.1313 | 7.8075 | 21.3749 |
| quality_target_mild | E | temporal | ExtraTrees | 814 | 772 | 42 | 0.0869 | 0.0977 | 5.2755 | 3.5291 | 10.5947 |
| quality_target_mild | F | temporal | LightGBM | 814 | 772 | 42 | -0.8544 | -1.1720 | 51.8590 | 42.3452 | 44.5118 |
| quality_target_mild | G | temporal | CatBoost | 814 | 772 | 42 | -0.2074 | -0.4261 | 30.3630 | 18.6188 | 26.8017 |
| quality_target_mild | H | temporal | NGBoost | 814 | 772 | 42 | 0.3638 | 0.3698 | 0.0544 | 0.0365 | 97.8839 |
| quality_target_strict | A | temporal | ElasticNet | 782 | 742 | 40 | 0.0165 | -0.0055 | 4.8393 | 3.8398 | 42.3326 |
| quality_target_strict | B | temporal | ElasticNet | 782 | 742 | 40 | 0.2433 | 0.1698 | 0.4609 | 0.3398 | 212.8309 |
| quality_target_strict | C | temporal | RF | 782 | 742 | 40 | -0.9386 | -1.2747 | 25.1932 | 22.6234 | 82.6887 |
| quality_target_strict | D | temporal | ElasticNet | 782 | 742 | 40 | 0.2390 | 0.2044 | 12.6861 | 7.9900 | 22.5491 |
| quality_target_strict | E | temporal | ExtraTrees | 782 | 742 | 40 | 0.0509 | 0.0514 | 5.3496 | 3.6599 | 11.0245 |
| quality_target_strict | F | temporal | LightGBM | 782 | 742 | 40 | -1.1783 | -1.4650 | 53.9753 | 43.6653 | 45.8455 |
| quality_target_strict | G | temporal | ExtraTrees | 782 | 742 | 40 | -0.0880 | -0.2749 | 28.6498 | 17.9261 | 23.8973 |
| quality_target_strict | H | temporal | CatBoost | 782 | 742 | 40 | 0.2068 | 0.1963 | 0.0393 | 0.0315 | 103.0939 |

## 输出文件

- 完整对照指标：`tables/cleaning_strategy_comparison.csv`
- 各策略各目标最佳指标：`tables/cleaning_strategy_best_metrics.csv`
- 清洗规则记录：`tables/cleaning_strategy_reports.json`
- 清洗后数据变体：`data/processed/cleaning_variants/`

目标变量极端值剔除会改变验证样本，论文中应作为敏感性分析或测量异常剔除说明；默认推荐优先采用 `quality`，除非有明确的异常值判定依据。
