# 本地材料摘要

本文件记录用于设计复现实验的本地材料要点。

## 预测main.pdf

- 页数：11
- 首页文本摘录：Journal of Hazardous Materials 458 (2023) 131900 Available online 19 June 2023 0304-3894/© 2023 Elsevier B.V. All rights reserved. A novel four-dimensional prediction model of soil heavy metal pollution: Geographical exp

### 关键词：parallel ensemble artificial intelligence

se Academy of Forestry, Beijing 100091, China f School of Data Science and Artificial Intelligence, Dongbei University of Finance & Economics, Dalian 116025, China HIGHLIGHTS GRAPHICAL ABSTRACT • Develop a soil heavy metal source-sink prediction model at 1 km spatial resolution. • Quantify spatio-temporal patterns and drivers of soil Cd at local to region 2016 – 2030. • Adopt TreeExplainer-based SHAP and parallel ensemble artificial intelligence models. • Beyond artificial intelligence "black box" to juggle interpretability and accuracy. • Advance approach for geographically precise prevention and control of soil pollutants. ARTICLE INFO Keywords: Soil pollutant Prediction Artificial intelligence Geographical explanation Ensemble learning TreeSHAP ABSTRACT The current artificial intelligence (AI)-b

### 关键词：TreeExplainer

h Institute of Forestry, Chinese Academy of Forestry, Beijing 100091, China f School of Data Science and Artificial Intelligence, Dongbei University of Finance & Economics, Dalian 116025, China HIGHLIGHTS GRAPHICAL ABSTRACT • Develop a soil heavy metal source-sink prediction model at 1 km spatial resolution. • Quantify spatio-temporal patterns and drivers of soil Cd at local to region 2016 – 2030. • Adopt TreeExplainer-based SHAP and parallel ensemble artificial intelligence models. • Beyond artificial intelligence "black box" to juggle interpretability and accuracy. • Advance approach for geographically precise prevention and control of soil pollutants. ARTICLE INFO Keywords: Soil pollutant Prediction Artificial intelligence Geographical explanation Ensemble learning TreeSHAP ABSTRACT The current

### 关键词：weighted ensemble

as over-fitting, each model was trained by 30 times. The three individual models with the best predic - tion performance were selected using the Standard Deviation (SD), Pearson ’ s correlation coefficient and root mean square deviation (RMSD) between the observed and the predicted of each AI model. To improve the accuracy and stability, the top three models were then paralleled combined into an ensemble by the weighted ensemble of mean square error (MSE) and R 2 . Model validation was performed. We thus obtained an ensemble black box prediction model of soil heavy metal contents. The information obtained is then the basis for the next explaining prediction. TreeExplainer-based SHAP (TreeSHAP) method was adopted to predict local explanations (the impact of input drivers on soil heavy metals in a specific spatial locat

## 预测1-s2.0-S0045653520311012-main.pdf

- 页数：9
- 首页文本摘录：Spatiotemporal modeling of soil heavy metals and early warnings from scenarios-based prediction Mingjiang He , Ping Yan , Haodan Yu , Shiyan Yang , Jianming Xu , Xingmei Liu * College of Environmental and Natural Resourc

### 关键词：scenario simulation

s and early warnings from scenarios-based prediction Mingjiang He , Ping Yan , Haodan Yu , Shiyan Yang , Jianming Xu , Xingmei Liu * College of Environmental and Natural Resource Sciences, Zhejiang Provincial Key Laboratory of Agricultural Resources and Environment, Zhejiang University, Hangzhou, 310058, China highlights grap hical abstract /C15 Driving force of soil heavy metal (SHM) increments was identi ﬁed. /C15 Scenario simulation model for SHM prediction was established. /C15 The probability of high ecological risks would be twice higher by 2026 without control. /C15 Recommendations were proposed towards agricultural soil environ- ment management. article info Article history: Received 7 January 2020 Received in revised form 20 April 2020 Accepted 25 April 2020 Available online 29 April 2020 Handling editor: Derek Muir Key

### 关键词：optimistic scenario

ts are zero under strict environmental policy) and default (the pollution status maintain constant) conditions. Results indicated that the paddy soil was contaminated mainly by Cd and Cu. Spatiotemporal maps revealed distinct patterns in the joint area, where soil Cd, Ni, Zn, Pb and Cu all increased in northwest. Soil heavy metal concentrations as well as the associated ecological risks would decline gradually under optimistic scenario, while sharply increase when no control acts are taken over long term in default condition. The percentages of soil Cd and Cu that exceeding their corresponding risk screening value (RSV) under the default condition would be 1.6 and 1.3 times higher than those under optimistic scenario 10 years later. The probability of high potential ecological risk in default condition would be twice higher than

### 关键词：default scenario

was con- ducted by combining qualitative analysis with quantitative equa- tion to predict soil heavy metal concentrations and trends under different assumed scenarios based on available information and judgement (Wu, 2008). It usually includes optimistic scenario (the pollution sources are zero under strict policy and measures), pessimistic scenario (worsening trend of soil pollution with more pollutants input) and default scenario (pollution level maintains the current status). The model is conducted in the following steps: determining the prediction theme, analyzing the future scenario, ﬁnding the in ﬂuencing factor, speci ﬁc analysis and prediction. In consideration of above views, the objectives of the present study were: 1) to clarify the spatiotemporal characteristics of soil Cd, Ni, Cu, Pb and Zn during 201 1 e2016; 2) t

### 关键词：spatiotemporal

Spatiotemporal modeling of soil heavy metals and early warnings from scenarios-based prediction Mingjiang He , Ping Yan , Haodan Yu , Shiyan Yang , Jianming Xu , Xingmei Liu * College of Environmental and Natural Resource Sciences, Zhejiang Provincial Key Laboratory of Agricultural Resources and Environment, Zhejiang University, Hangzhou, 310058, China highlights grap hical abstract /C15 Driving force of soil heavy m

## 方案文档要点

- 一、研究目标与核心问题
- （一）研究目标
- 响应变量：研究目标为土壤重金属含量，本方案统一标记为变量Y，可根据实际数据列名明确Cd、Cu、Pb、Zn等具体重金属指标。
- 3.3 模型选择与集成策略
- 3.5 模型验证与对比体系
- 3.6 模型可解释性分析（SCI核心亮点）
- 四、未来情景设计
- 可解释性与不确定性分析：计算SHAP解释值，执行Bootstrap抽样量化预测误差；
- 七、论文撰写注意事项（提升SCI录用率）
- 强化地理可解释性：弱化“黑箱模型”表述，重点阐述驱动因子作用机理、重金属空间分异的地理成因，凸显研究地理学价值。
