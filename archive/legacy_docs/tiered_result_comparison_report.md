# 分层结果对比

本报告把四种口径放在同一张图中：论文主结果、探索上限、线性同集上限和 NNLS 留一诊断。论文主结果不使用 2022-2026 目标值调参；探索上限与线性同集上限使用了验证集观测值进行候选选择、权重拟合或同集拟合，只能作为上限诊断；留一诊断用于显示同集上限的稳定性。

| tier | mean_r2 | median_r2 | min_r2 | max_r2 | n_positive |
| --- | --- | --- | --- | --- | --- |
| Publication-grade | 0.3993 | 0.4111 | 0.0793 | 0.6800 | 8 |
| Exploration upper | 0.9000 | 0.9776 | 0.6469 | 1.0000 | 8 |
| Linear same-set upper | 0.9744 | 0.9908 | 0.8642 | 1.0000 | 8 |
| NNLS LOO diagnostic | 0.0769 | 0.2625 | -1.2887 | 0.5035 | 6 |

图件：`figures/tiered_results/tiered_r2_comparison.png`。

逐目标对比表见 `tables/tiered_result_comparison.csv`；摘要表见 `tables/tiered_result_summary.csv`。
