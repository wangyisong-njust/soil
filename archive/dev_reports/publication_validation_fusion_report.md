# 论文口径验证期融合

该实验只使用 2019-2020 验证期来选择模型或拟合融合权重，然后固定应用到 2021-2026。它不使用 2021-2026 目标值调参，比 NNLS 同集探索更适合作为论文主结果候选。

| target | model | n_members | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | ValNNLS10 | 4 | 0.2452 | 14.0922 | 7.0002 | 52.8018 |
| B | Top12InvRMSEMean | 12 | 0.5972 | 2.2799 | 1.1266 | 319.8649 |
| C | Top8Median | 8 | -0.1472 | 38.7910 | 30.2322 | 86.8943 |
| D | Top2InvRMSEMean | 2 | 0.2265 | 37.8029 | 18.7983 | 45.5647 |
| E | Top20InvRMSEMean | 20 | 0.2364 | 17.2991 | 8.3106 | 24.3747 |
| F | ValNNLS40 | 4 | -0.0294 | 974.4165 | 203.8878 | 56.7393 |
| G | ValRidge20Clipped | 20 | -1.1178 | 57.5354 | 40.7650 | 62.6695 |
| H | ValBestRMSE | 1 | 0.0157 | 0.7891 | 0.2350 | 231.2859 |

完整结果见 `tables/publication_validation_fusion_metrics.csv`；最优结果见 `tables/publication_validation_fusion_best_metrics.csv`。
