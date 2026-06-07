# 论文口径验证期融合

该实验只使用 2019-2020 验证期来选择模型或拟合融合权重，然后固定应用到 2022-2026。它不使用 2022-2026 目标值调参，比 NNLS 同集探索更适合作为论文主结果候选。

| target | model | n_members | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | ValRidge20Clipped | 20 | 0.2083 | 17.0887 | 7.0247 | 53.1484 |
| B | ValNNLS20 | 4 | 0.1010 | 1.9500 | 0.8898 | 334.5455 |
| C | Top3Median | 3 | -0.0062 | 34.1246 | 22.4185 | 58.5994 |
| D | ValRidge40Clipped | 40 | 0.3383 | 40.9972 | 17.9470 | 35.4637 |
| E | Top12InvRMSEMean | 12 | 0.1917 | 21.8784 | 10.2187 | 23.9956 |
| F | ValBestRMSE | 1 | 0.3414 | 65.2850 | 39.7116 | 30.9393 |
| G | Top20Median | 20 | -0.0078 | 27.5455 | 21.0244 | 42.4833 |
| H | ValNNLS5NormClipQ05_95 | 2 | -0.0815 | 0.2452 | 0.1292 | 228.9223 |

完整结果见 `tables/publication_validation_fusion_metrics.csv`；最优结果见 `tables/publication_validation_fusion_best_metrics.csv`。
