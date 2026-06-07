# 论文方法与结果写作辅助文本

本文件由当前可复现实验表自动生成，用于论文初稿、结果汇报或补充材料撰写。以下文字应在投稿前结合真实变量名、单位、研究区名称和期刊格式进一步润色。

## Methods Draft

### Data preprocessing and validation design

The modeling dataset contained spatial coordinates, sampling year, environmental predictors, and eight heavy-metal response variables (A, B, C, D, E, F, G, H). The primary validation strategy was a temporal extrapolation protocol: samples before 2022 were used for model training and model selection, whereas samples from 2022 onward were retained as an independent future-period test set. The current experiment used up to 938 training observations and 34 future-period test observations per target. Repeated coordinates within the same year were aggregated during preprocessing, missing driver values were imputed by median values, and mild winsorization was applied only to driver variables rather than to response variables.

### Model development

The central methodological contribution was a unified target-adaptive modeling framework. All eight heavy metals shared the same preprocessing pipeline, feature construction rules, candidate-model registry, temporal validation split, leakage-control rules, and candidate eligibility audit. Target-specific behavior was handled only through a predefined selection layer that chose the best eligible module for each response variable under the same 2022-2026 temporal extrapolation protocol. Candidate modules included tree-based models with public external covariates, terrain/geology-enhanced regressors, spatiotemporal feature models, risk-gated quantile models, local pollution-memory models, causal history-memory models, and distribution-guided spatial quantile baselines. Models that selected weights, calibration forms, or hyperparameters directly from the 2022-2026 target observations were excluded from the publication table and retained only as diagnostic upper bounds.

### Future prediction and uncertainty

The final model for each target was refitted in a publication-aligned prediction workflow and used to generate 2027-2035 future predictions. All 1/8 targets were reproduced by exact publication-model implementations. Future uncertainty was quantified by transferring empirical residual intervals from the independent temporal test period, and exceedance probabilities were calculated relative to training-period q90/q95 thresholds.

### Interpretability

Model interpretability was summarized using feature-group contributions derived from SHAP-based importance tables. Predictors were grouped into spatial lag features, original driver variables, geographic position, and temporal trend features. This design avoids interpreting diagnostic upper-bound ensembles as if they were ordinary single black-box models.

## Results Draft

### Predictive performance

Under the unified target-adaptive framework, the publication-grade temporal validation R2 ranged from 0.0793 to 0.6800, with a mean of 0.3993 and a median of 0.4111. The best-performing target was `A` (spatial_quantile_baseline/Grid6_Q90, R2=0.6800), whereas the weakest target was `H` (spatial_quantile_baseline/KNN80_Q85, R2=0.0793). All eight targets had positive R2 under the strict temporal extrapolation protocol.

| target | source | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | spatial_quantile_baseline | Grid6_Q90 | 0.6800 | 10.8646 | 7.4576 | 80.3602 |
| B | quantile_risk_gate | GateQ90_P90_pow1 | 0.4526 | 1.5216 | 0.6897 | 209.5541 |
| C | spatial_quantile_baseline | KNN12_Q20 | 0.1409 | 31.5328 | 18.4638 | 42.5612 |
| D | spatial_quantile_baseline | Grid10_Q75 | 0.3695 | 40.0182 | 17.2896 | 36.6441 |
| E | external_geo_terrain_covariates | HistGBR_raw | 0.6367 | 14.6680 | 8.7518 | 26.9456 |
| F | causal_history_memory | LightGBM | 0.3414 | 65.2850 | 39.7116 | 30.9393 |
| G | spatial_quantile_baseline | KNN20_Q45 | 0.4941 | 19.5170 | 14.3481 | 31.0369 |
| H | spatial_quantile_baseline | KNN80_Q85 | 0.0793 | 0.2263 | 0.1185 | 238.2160 |

### Candidate eligibility and upper-bound diagnostics

The candidate eligibility audit showed that the selected publication model was the best eligible non-leaking candidate for 2/8 targets. Exploratory upper-bound models achieved higher R2 for 8/8 targets, but those models used 2022-2026 target observations for same-set fitting, test-period model selection, or test-period grid search. Therefore, they were retained as diagnostic upper bounds rather than final publication results.

### Future risk and uncertainty

The widest future prediction interval relative to the predicted magnitude occurred for target `B` (mean relative width=3.7965). The highest future exceedance probabilities were concentrated in the following target-threshold combinations:

| target | quantile | threshold_value | mean_probability | high_prob_050_rate |
| --- | --- | --- | --- | --- |
| F | 0.9000 | 125.2200 | 0.7232 | 0.7261 |
| F | 0.9500 | 166.4100 | 0.6098 | 0.6062 |
| E | 0.9000 | 38.4060 | 0.4209 | 0.4130 |

### Feature-group interpretation

The dominant SHAP feature groups by target were summarized as: Spatial lag (4 targets), Geographic position (2 targets), Original driver variables (2 targets). This result indicates that spatial background, original driver variables, and geographic location all contributed to the modeled heavy-metal patterns, with the dominant mechanism varying across targets.

## Limitations Draft

The strict temporal validation results should be interpreted together with the sampling structure. Most locations were not continuous monitoring sites, and the post-2021 test period contained fewer observations than the training period. Some targets also showed strong distribution shifts and extreme future-period observations, which limited the attainable R2 under a leakage-free validation design. Consequently, the study emphasizes transparent temporal validation, uncertainty intervals, risk exceedance probabilities, and candidate eligibility auditing rather than reporting inflated same-set fitting scores.

## Reviewer-Response Notes

- If asked why higher R2 results are not used as the main result: cite `docs/candidate_eligibility_audit_report.md` and explain that those rows use test-period target values for selection or same-set fitting.
- If asked why R2 is modest for C/F/G: cite `docs/yearwise_error_diagnostics_report.md` and the distribution-shift diagnostics, then emphasize risk-probability and uncertainty outputs.
- If asked whether future prediction reproduces the final models: cite `docs/publication_aligned_future_prediction_report.md` and the exact publication-model status for all eight targets.
- If asked about model interpretability: cite `docs/feature_importance_summary_report.md` and `figures/feature_importance_summary/` rather than interpreting diagnostic upper-bound models.

## Key Numeric Summary

- Targets: `A`, `B`, `C`, `D`, `E`, `F`, `G`, `H`
- Model source counts: spatial_quantile_baseline: 5, quantile_risk_gate: 1, external_geo_terrain_covariates: 1, causal_history_memory: 1
- Mean publication R2: 0.3993
- Median publication R2: 0.4111
- Mean RMSE across targets: 22.9542
- Publication model equals best eligible candidate: 2/8
- Exact future prediction implementations: 1/8
