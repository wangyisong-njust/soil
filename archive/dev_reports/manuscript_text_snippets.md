# 论文方法与结果写作辅助文本

本文件由当前可复现实验表自动生成，用于论文初稿、结果汇报或补充材料撰写。以下文字应在投稿前结合真实变量名、单位、研究区名称和期刊格式进一步润色。

## Methods Draft

### Data preprocessing and validation design

The modeling dataset contained spatial coordinates, sampling year, environmental predictors, and eight heavy-metal response variables (A, B, C, D, E, F, G, H). The primary validation strategy was a temporal extrapolation protocol: samples before 2021 were used for model training and model selection, whereas samples from 2021 onward were retained as an independent future-period test set. The current experiment used up to 915 training observations and 57 future-period test observations per target. Repeated coordinates within the same year were aggregated during preprocessing, missing driver values were imputed by median values, and mild winsorization was applied only to driver variables rather than to response variables.

### Model development

A target-adaptive modeling framework was used because the eight heavy metals showed different spatial distributions, temporal stability, and sensitivity to extreme values. Candidate models included tree-based machine learning models with public external covariates, spatiotemporal feature models, temporal sequence baselines, distributionally robust regressors, local analog memory models, distribution-guided spatial quantile models, and validation-defined fusion models. For the final publication table, models that selected weights, calibration forms, or hyperparameters directly from the 2021-2026 target observations were excluded and retained only as diagnostic upper bounds.

### Future prediction and uncertainty

The final model for each target was refitted in a publication-aligned prediction workflow and used to generate 2027-2035 future predictions. All 8/8 targets were reproduced by exact publication-model implementations. Future uncertainty was quantified by transferring empirical residual intervals from the independent temporal test period, and exceedance probabilities were calculated relative to training-period q90/q95 thresholds.

### Interpretability

Model interpretability was summarized using feature-group contributions derived from SHAP-based importance tables. Predictors were grouped into spatial lag features, original driver variables, geographic position, and temporal trend features. This design avoids interpreting diagnostic upper-bound ensembles as if they were ordinary single black-box models.

## Results Draft

### Predictive performance

Across the eight targets, the publication-grade temporal validation R2 ranged from 0.0140 to 0.5972, with a mean of 0.2645 and a median of 0.2273. The best-performing target was `B` (publication_validation_fusion/Top12InvRMSEMean, R2=0.5972), whereas the weakest target was `F` (distribution_guided_spatial_quantile/Grid2_Q96, R2=0.0140). All eight targets had positive R2 under the strict temporal extrapolation protocol.

| target | source | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | external_public_covariates | LightGBM | 0.3559 | 13.0177 | 6.3821 | 40.5567 |
| B | publication_validation_fusion | Top12InvRMSEMean | 0.5972 | 2.2799 | 1.1266 | 319.8649 |
| C | distribution_guided_spatial_quantile | KNN12_Q25 | 0.0561 | 35.1860 | 20.9462 | 47.9229 |
| D | external_geo_terrain_covariates | ExtraTrees | 0.2648 | 36.8555 | 15.5121 | 33.6195 |
| E | external_geo_terrain_covariates | XGBoost | 0.5570 | 13.1763 | 6.8337 | 22.5792 |
| F | distribution_guided_spatial_quantile | Grid2_Q96 | 0.0140 | 953.6686 | 269.2298 | 191.6443 |
| G | distribution_guided_spatial_quantile | Grid5_Q50 | 0.0812 | 37.8970 | 22.4388 | 33.5596 |
| H | local_analog_memory | HistGBR | 0.1898 | 0.7160 | 0.1855 | 149.9495 |

### Candidate eligibility and upper-bound diagnostics

The candidate eligibility audit showed that the selected publication model was the best eligible non-leaking candidate for 8/8 targets. Exploratory upper-bound models achieved higher R2 for 8/8 targets, but those models used 2021-2026 target observations for same-set fitting, test-period model selection, or test-period grid search. Therefore, they were retained as diagnostic upper bounds rather than final publication results.

### Future risk and uncertainty

The widest future prediction interval relative to the predicted magnitude occurred for target `B` (mean relative width=7.2231). The highest future exceedance probabilities were concentrated in the following target-threshold combinations:

| target | quantile | threshold_value | mean_probability | high_prob_050_rate |
| --- | --- | --- | --- | --- |
| F | 0.9000 | 125.2200 | 0.8934 | 1.0000 |
| F | 0.9500 | 166.4100 | 0.7669 | 0.6964 |
| E | 0.9000 | 38.4060 | 0.2281 | 0.0955 |

### Feature-group interpretation

The dominant SHAP feature groups by target were summarized as: Spatial lag (6 targets), Original driver variables (2 targets). This result indicates that spatial background, original driver variables, and geographic location all contributed to the modeled heavy-metal patterns, with the dominant mechanism varying across targets.

## Limitations Draft

The strict temporal validation results should be interpreted together with the sampling structure. Most locations were not continuous monitoring sites, and the post-2021 test period contained fewer observations than the training period. Some targets also showed strong distribution shifts and extreme future-period observations, which limited the attainable R2 under a leakage-free validation design. Consequently, the study emphasizes transparent temporal validation, uncertainty intervals, risk exceedance probabilities, and candidate eligibility auditing rather than reporting inflated same-set fitting scores.

## Reviewer-Response Notes

- If asked why higher R2 results are not used as the main result: cite `docs/candidate_eligibility_audit_report.md` and explain that those rows use test-period target values for selection or same-set fitting.
- If asked why R2 is modest for C/F/G: cite `docs/yearwise_error_diagnostics_report.md` and the distribution-shift diagnostics, then emphasize risk-probability and uncertainty outputs.
- If asked whether future prediction reproduces the final models: cite `docs/publication_aligned_future_prediction_report.md` and the exact publication-model status for all eight targets.
- If asked about model interpretability: cite `docs/feature_importance_summary_report.md` and `figures/feature_importance_summary/` rather than interpreting diagnostic upper-bound models.

## Key Numeric Summary

- Targets: `A`, `B`, `C`, `D`, `E`, `F`, `G`, `H`
- Model source counts: distribution_guided_spatial_quantile: 3, external_geo_terrain_covariates: 2, external_public_covariates: 1, publication_validation_fusion: 1, local_analog_memory: 1
- Mean publication R2: 0.2645
- Median publication R2: 0.2273
- Mean RMSE across targets: 136.5996
- Publication model equals best eligible candidate: 8/8
- Exact future prediction implementations: 8/8
