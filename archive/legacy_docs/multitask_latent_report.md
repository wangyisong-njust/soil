# 多任务潜变量模型对照

该模型先在训练期 8 个重金属 log 浓度上提取 PCA 综合污染潜因子，再由环境因子和空间分区特征预测潜因子，最后重构各重金属浓度。验证期其他重金属不作为输入。

| protocol | target | model | n_train | n_test | n_components | pca_explained_variance | r2 | r2_log1p | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| literature_2019_2020 | A | Latent_ExtraTrees | 815 | 100 | 4 | 0.8415 | 0.1622 | 0.2236 | 12.7947 | 6.1239 | 34.4452 |
| literature_2019_2020 | B | Latent_RF | 815 | 100 | 4 | 0.8415 | -0.0118 | -0.1252 | 2.1866 | 1.0032 | 230.4637 |
| literature_2019_2020 | C | Latent_ExtraTrees | 815 | 100 | 4 | 0.8415 | -0.0012 | 0.0393 | 52.4331 | 23.9923 | 34.1809 |
| literature_2019_2020 | D | Latent_ExtraTrees | 815 | 100 | 4 | 0.8415 | 0.0908 | 0.0336 | 54.8876 | 21.7888 | 48.8525 |
| literature_2019_2020 | E | Latent_PLSR | 815 | 100 | 4 | 0.8415 | 0.0074 | 0.0318 | 11.1857 | 7.3508 | 26.8458 |
| literature_2019_2020 | F | Latent_ExtraTrees | 815 | 100 | 4 | 0.8415 | 0.1125 | 0.2565 | 80.8541 | 39.6626 | 71.6069 |
| literature_2019_2020 | G | Latent_ExtraTrees | 815 | 100 | 4 | 0.8415 | -0.0033 | -0.0873 | 124.8082 | 50.3210 | 41.6778 |
| literature_2019_2020 | H | Latent_RF | 815 | 100 | 4 | 0.8415 | 0.0132 | 0.0370 | 0.3547 | 0.1289 | 83.5310 |
| temporal_2022_2026 | A | Latent_Ridge | 938 | 34 | 4 | 0.8364 | 0.1135 | -0.0692 | 18.0828 | 8.4472 | 74.9211 |
| temporal_2022_2026 | B | Latent_ExtraTrees | 938 | 34 | 4 | 0.8364 | 0.1078 | 0.1050 | 1.9426 | 0.8810 | 388.7425 |
| temporal_2022_2026 | C | Latent_ExtraTrees | 938 | 34 | 4 | 0.8364 | -0.0395 | -0.3234 | 34.6846 | 23.5660 | 68.2791 |
| temporal_2022_2026 | D | Latent_ExtraTrees | 938 | 34 | 4 | 0.8364 | 0.0578 | 0.1964 | 48.9191 | 17.4656 | 28.4826 |
| temporal_2022_2026 | E | Latent_Ridge | 938 | 34 | 4 | 0.8364 | -0.0361 | 0.0099 | 24.7698 | 11.0753 | 25.9412 |
| temporal_2022_2026 | F | Latent_ExtraTrees | 938 | 34 | 4 | 0.8364 | -0.1283 | -0.9372 | 85.4465 | 53.0500 | 38.8864 |
| temporal_2022_2026 | G | Latent_Ridge | 938 | 34 | 4 | 0.8364 | 0.0317 | -0.1622 | 27.0005 | 23.0088 | 41.9319 |
| temporal_2022_2026 | H | Latent_RF | 938 | 34 | 4 | 0.8364 | 0.0759 | 0.0844 | 0.2267 | 0.1299 | 268.8980 |

输出文件：

- `tables/multitask_latent_metrics.csv`
- `tables/multitask_latent_best_metrics.csv`
- `results/multitask_latent_predictions.csv`
