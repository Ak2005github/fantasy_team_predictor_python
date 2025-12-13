# IPL Fantasy Team Predictor Analytics

## Table of Contents

- [Brief One-Line Summary](#brief-one-line-summary)
- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Dataset](#dataset)
- [Tools and Technologies](#tools-and-technologies)
- [Methods](#methods)
- [Key Insights](#key-insights)
- [Dashboard / Model / Output](#dashboard--model--output)
- [How to Run This Project?](#how-to-run-this-project)
- [Results & Conclusion](#results--conclusion)
- [Future Work](#future-work)
- [Author & Contact](#author--contact)

---

# IPL Fantasy Team Predictor Analytics

## Brief One-Line Summary

An end-to-end data pipeline for scraping, processing, and engineering player-level cricket performance features for IPL fantasy analytics and modeling.

---

## Overview

This project builds a reproducible analytics pipeline that collects historical IPL player data from public cricket sources, cleans and standardizes it, computes fantasy scoring metrics, and generates structured, model-ready features at the player and match level. The repository is designed with a strong separation between raw data, processed artifacts, and reusable source code, following industry-standard data science and ML engineering practices.

---

## Problem Statement

Fantasy sports platforms and analysts require consistent, high-quality player performance features to evaluate and predict outcomes. However, cricket data is fragmented across sources, inconsistently formatted, and not directly suitable for modeling. This project addresses the challenge of:

- Consolidating player-level data across formats and sources
- Applying standardized fantasy scoring rules
- Generating clean, reproducible feature sets for downstream analytics and modeling

---

## Dataset

The project uses a combination of:

- Publicly available IPL match and player statistics scraped from cricket data sources
- Squad and match reference files for player identification and alignment

**Data policy:**

- Small, reference datasets (squad lists, match metadata, player ID mappings) are versioned in the repository
- Large, generated datasets such as per-player CSVs and feature outputs are excluded and regenerated via the pipeline
- A sample dataset may be included to demonstrate schema and structure

---

## Tools and Technologies

- Python
- Pandas, NumPy
- Requests, BeautifulSoup (for scraping)
- Jupyter Notebook (EDA and validation)
- Git & GitHub

---

## Methods

1. **Data Collection**

   - Scraping player-wise batting, bowling, and fielding data
   - Resolving player identifiers across sources

2. **Preprocessing**

   - Cleaning raw CSV and Excel inputs
   - Normalizing column names and formats
   - Aligning match dates and metadata

3. **Fantasy Scoring**

   - Applying rule-based fantasy point calculations for batting, bowling, and fielding

4. **Feature Engineering**

   - Rolling and aggregate player statistics
   - Match- and venue-aware contextual features
   - Generation of model-ready feature tables

---

## Key Insights

- Player performance trends vary significantly based on venue and match context
- Rolling historical features provide more stability than raw match-level statistics
- Separating raw data, processed data, and artifacts greatly improves reproducibility and scalability

---

## Dashboard / Model / Output

The primary outputs of this project are:

- Clean, structured feature tables at the player and match level
- Aggregated datasets suitable for machine learning models or dashboards

Modeling and visualization layers can be built on top of these outputs as extensions.

---

## How to Run This Project?

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the data pipeline:
   ```bash
   python scripts/run_pipeline.py
   ```
4. Explore analysis notebooks in the `notebooks/` directory

---

## Results & Conclusion

The project delivers a scalable and maintainable pipeline for IPL fantasy analytics, transforming raw and inconsistent cricket data into high-quality, reusable features. The structure and methodology make it suitable for further experimentation, modeling, and deployment in fantasy sports or sports analytics use cases.

---

## Future Work

- Integration of predictive models for fantasy point forecasting
- Automation using scheduled pipelines
- Addition of team-level and opposition-aware features
- Dashboarding using BI or web frameworks

---

## Author & Contact

**Author:** Akshith 

Email: [akshith0104@gmail.com](mailto\:akshith0104@gmail.comor)

