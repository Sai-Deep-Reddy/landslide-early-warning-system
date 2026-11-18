| System | ROC-AUC (95% CI) | PR-AUC | Recall | Precision | FPR |
|---|---|---|---|---|---|
| I-D threshold rule (published, ratio>=1) | 0.643 (0.466-0.804) | 0.218 | 0.909 | 0.175 | 0.712 |
| Physics FoS alone | 0.671 (0.458-0.854) | 0.349 | 1.0 | 0.143 | 1.0 |
| XGBoost alone (monotone) | 0.53 (0.361-0.706) | 0.158 | 0.909 | 0.175 | 0.712 |
| Old fixed blend 0.55*ML + 0.45*physics | 0.652 (0.464-0.825) | 0.229 | 0.909 | 0.161 | 0.788 |
| Learned meta-learner (L2 logistic stacking) | 0.518 (0.314-0.708) | 0.177 | 0.636 | 0.135 | 0.682 |
