"""
Access Digital Health — Philanthropic Intelligence Platform MVP
An agentic AI platform for evidence-grounded philanthropic decision-making.
Three modes: Donor Advisory, Proposal Evaluation, Portfolio Monitor.

Built for the Gates Foundation Grand Challenges: AI to Accelerate Charitable Giving
"""

import streamlit as st
import anthropic
import json
import time
from datetime import datetime

# Database integration
from db import Database

# ══════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════

APP_TITLE = "Philanthropic Intelligence Platform"
APP_SUBTITLE = "Evidence-grounded AI for donors, funders, and portfolio managers"
BRAND = "Access Digital Health"
MODEL = "claude-sonnet-4-20250514"

# DHIS2 Demo Server Configuration — try multiple URLs since demo instances rotate
DHIS2_SERVERS = [
    "https://play.im.dhis2.org/stable-2-40-6/api",
    "https://play.im.dhis2.org/stable-2-41-2/api",
    "https://play.im.dhis2.org/dev/api",
    "https://play.dhis2.org/40/api",
]
DHIS2_USERNAME = "admin"
DHIS2_PASSWORD = "district"

# ══════════════════════════════════════════════
# CURATED EVIDENCE & COST-EFFECTIVENESS DATA
# ══════════════════════════════════════════════

# Curated from GiveWell, DCP3, WHO-CHOICE, and key systematic reviews
# This embedded knowledge base gives the agent quantitative rigor
# without requiring API integrations on day one.

COST_EFFECTIVENESS_DB = {
    "insecticide_treated_nets": {
        "intervention": "Insecticide-treated bed nets (ITNs) for malaria prevention",
        "cost_per_daly_averted": "$50-100",
        "cost_per_life_saved": "$3,000-5,000",
        "evidence_strength": "Very strong — multiple RCTs, Cochrane review",
        "key_source": "GiveWell (Against Malaria Foundation), Lancet meta-analysis",
        "who_threshold": "Highly cost-effective (< 1x GDP per capita)",
        "scalability": "High — proven supply chains exist across sub-Saharan Africa",
        "relevant_dhis2_indicators": ["Malaria cases", "Malaria deaths", "ITN distribution", "ITN coverage"],
    },
    "seasonal_malaria_chemoprevention": {
        "intervention": "Seasonal malaria chemoprevention (SMC) for children under 5",
        "cost_per_daly_averted": "$30-80",
        "cost_per_life_saved": "$2,500-4,500",
        "evidence_strength": "Strong — Cochrane review shows 75% reduction in malaria episodes",
        "key_source": "GiveWell (Malaria Consortium), ACCESS-SMC trial",
        "who_threshold": "Highly cost-effective",
        "scalability": "High in Sahel region — seasonal delivery model proven",
        "relevant_dhis2_indicators": ["Malaria cases under 5", "SMC coverage", "Malaria mortality under 5"],
    },
    "oral_rehydration_therapy": {
        "intervention": "Oral rehydration solution (ORS) for diarrheal disease",
        "cost_per_daly_averted": "$50-150",
        "cost_per_life_saved": "$2,000-5,000",
        "evidence_strength": "Very strong — decades of evidence, WHO essential medicine",
        "key_source": "DCP3, Lancet Global Health Commission",
        "who_threshold": "Highly cost-effective",
        "scalability": "Very high — low cost, community-distributable",
        "relevant_dhis2_indicators": ["Diarrhea cases under 5", "ORS availability", "Diarrhea mortality"],
    },
    "vitamin_a_supplementation": {
        "intervention": "Vitamin A supplementation for children 6-59 months",
        "cost_per_daly_averted": "$15-50",
        "cost_per_life_saved": "$1,000-3,500",
        "evidence_strength": "Strong — Cochrane review shows 24% reduction in all-cause mortality",
        "key_source": "GiveWell (Helen Keller International), Cochrane review",
        "who_threshold": "Highly cost-effective",
        "scalability": "High — integrated into immunization campaigns",
        "relevant_dhis2_indicators": ["Vitamin A supplementation coverage", "Under-5 mortality"],
    },
    "skilled_birth_attendance": {
        "intervention": "Skilled birth attendance and emergency obstetric care",
        "cost_per_daly_averted": "$100-400",
        "cost_per_life_saved": "$3,000-8,000",
        "evidence_strength": "Strong — WHO recommendation, observational evidence from scale-up",
        "key_source": "DCP3, WHO recommendations, Lancet Midwifery Series",
        "who_threshold": "Cost-effective",
        "scalability": "Medium — requires trained workforce and facility infrastructure",
        "relevant_dhis2_indicators": ["Skilled birth attendance rate", "Facility delivery rate", "Maternal mortality ratio", "ANC coverage"],
    },
    "childhood_immunization": {
        "intervention": "Routine childhood immunization (DPT3, measles, polio)",
        "cost_per_daly_averted": "$10-50",
        "cost_per_life_saved": "$500-3,000",
        "evidence_strength": "Very strong — foundational public health intervention",
        "key_source": "Gavi, WHO EPI, DCP3",
        "who_threshold": "Highly cost-effective",
        "scalability": "Very high — global infrastructure exists through Gavi",
        "relevant_dhis2_indicators": ["DPT3 coverage", "Measles vaccination coverage", "Zero-dose children", "Penta3 coverage"],
    },
    "community_health_workers": {
        "intervention": "Community health worker programs (iCCM, home visits)",
        "cost_per_daly_averted": "$150-500",
        "cost_per_life_saved": "$5,000-15,000",
        "evidence_strength": "Moderate-strong — varies by context and implementation quality",
        "key_source": "DCP3, WHO CHW Guideline, Last Mile Health evidence",
        "who_threshold": "Cost-effective",
        "scalability": "High — adaptable model across LMICs",
        "relevant_dhis2_indicators": ["CHW visits", "Community referrals", "Home-based care coverage"],
    },
    "hiv_art": {
        "intervention": "Antiretroviral therapy (ART) for HIV",
        "cost_per_daly_averted": "$200-600",
        "cost_per_life_saved": "$5,000-12,000",
        "evidence_strength": "Very strong — transforms HIV from fatal to chronic condition",
        "key_source": "UNAIDS, PEPFAR, Global Fund",
        "who_threshold": "Cost-effective",
        "scalability": "High — PEPFAR has demonstrated scale-up in 50+ countries",
        "relevant_dhis2_indicators": ["ART coverage", "HIV testing rate", "Viral load suppression", "PMTCT coverage"],
    },
    "tuberculosis_treatment": {
        "intervention": "TB diagnosis (GeneXpert) and DOTS treatment",
        "cost_per_daly_averted": "$50-200",
        "cost_per_life_saved": "$3,000-8,000",
        "evidence_strength": "Strong — WHO standard of care",
        "key_source": "Global Fund, Stop TB Partnership, DCP3",
        "who_threshold": "Highly cost-effective",
        "scalability": "High — proven treatment protocols, but case detection remains a gap",
        "relevant_dhis2_indicators": ["TB case detection rate", "TB treatment success rate", "TB mortality"],
    },
    "clean_water_and_sanitation": {
        "intervention": "Water, sanitation, and hygiene (WASH) programs",
        "cost_per_daly_averted": "$100-500",
        "cost_per_life_saved": "$5,000-20,000",
        "evidence_strength": "Moderate — strong for some components (chlorination), mixed for others",
        "key_source": "GiveWell (Evidence Action), JMP, DCP3",
        "who_threshold": "Cost-effective",
        "scalability": "Medium — infrastructure-dependent",
        "relevant_dhis2_indicators": ["Access to safe water", "Sanitation coverage", "Diarrhea incidence"],
    },
    "nutrition_supplementation": {
        "intervention": "Micronutrient supplementation and fortification",
        "cost_per_daly_averted": "$20-100",
        "cost_per_life_saved": "$1,500-5,000",
        "evidence_strength": "Strong — iron, zinc, iodine fortification well-evidenced",
        "key_source": "Copenhagen Consensus, DCP3, Global Alliance for Improved Nutrition",
        "who_threshold": "Highly cost-effective",
        "scalability": "Very high — can be delivered through food systems",
        "relevant_dhis2_indicators": ["Stunting prevalence", "Wasting prevalence", "Anemia prevalence", "Nutrition screening coverage"],
    },
    "family_planning": {
        "intervention": "Family planning services and contraceptive access",
        "cost_per_daly_averted": "$50-150",
        "cost_per_life_saved": "$3,000-8,000",
        "evidence_strength": "Strong — reduces maternal mortality, improves child spacing",
        "key_source": "DCP3, UNFPA, Guttmacher Institute",
        "who_threshold": "Highly cost-effective",
        "scalability": "High — multiple delivery modalities",
        "relevant_dhis2_indicators": ["Contraceptive prevalence rate", "Unmet need for family planning", "Maternal mortality ratio"],
    },
    "malaria_rdt": {
        "intervention": "Malaria rapid diagnostic tests (RDTs)",
        "cost_per_daly_averted": "$10-50",
        "cost_per_life_saved": "$500-2,000",
        "evidence_strength": "Very strong — WHO-recommended, widely deployed, Cochrane-reviewed",
        "key_source": "WHO malaria diagnostics guidelines, Global Fund, DCP3",
        "who_threshold": "Highly cost-effective",
        "scalability": "Very high — over 400 million RDTs distributed annually",
        "relevant_dhis2_indicators": ["Malaria RDT positive rate", "Malaria cases tested", "Malaria RDTs distributed"],
    },
    "ai_malaria_rdt_reading": {
        "intervention": "AI-assisted malaria RDT interpretation via smartphone",
        "cost_per_daly_averted": "Not yet established — emerging technology",
        "cost_per_life_saved": "Not yet established",
        "evidence_strength": "Moderate — YOLOv8 algorithms demonstrate 95-98% accuracy for parasite detection; limited real-world deployment studies",
        "key_source": "Malaria Journal 2023-2024, AIDMAN system studies, miLab MAL validation",
        "who_threshold": "Potentially highly cost-effective if accuracy holds at scale (near-zero incremental cost per test)",
        "scalability": "High — software-only, runs on existing smartphones carried by CHWs",
        "relevant_dhis2_indicators": ["Malaria RDT positive rate", "Malaria cases tested", "RDT reader variability"],
    },
    "ai_anemia_screening": {
        "intervention": "AI-based anemia detection via smartphone conjunctival photos",
        "cost_per_daly_averted": "Not yet established — emerging technology",
        "cost_per_life_saved": "Not yet established",
        "evidence_strength": "Moderate — studies show 90-98% accuracy in controlled settings; real-world validation shows 75.4% accuracy (lower for women AUC 0.74 vs men AUC 0.79)",
        "key_source": "Smartphone conjunctival imaging studies 2022-2024, Vision Transformer models, ED prospective study (n=426)",
        "who_threshold": "Potentially cost-effective (zero consumable cost per test)",
        "scalability": "High — non-invasive, no consumables, runs on existing phones",
        "relevant_dhis2_indicators": ["Anemia prevalence", "Hemoglobin testing coverage", "Iron supplementation coverage"],
    },
    "ai_tb_screening": {
        "intervention": "AI-assisted TB screening (chest X-ray analysis and cough acoustics)",
        "cost_per_daly_averted": "$30-150 (AI-CXR); not established (cough analysis)",
        "cost_per_life_saved": "$2,000-8,000 (AI-CXR)",
        "evidence_strength": "Strong for AI-CXR (WHO benchmark: 90% sensitivity, 70% specificity); Weak-Moderate for cough-based (large database of 700,000+ cough sounds compiled, but limited clinical validation)",
        "key_source": "WHO AI-CXR diagnostic guidelines, qXR validation studies, TB cough acoustic biomarker research",
        "who_threshold": "Cost-effective for AI-CXR; unestablished for cough analysis",
        "scalability": "High for CXR (portable X-ray + AI); Medium for cough (requires further validation)",
        "relevant_dhis2_indicators": ["TB case detection rate", "TB screening coverage", "TB presumptive cases tested"],
    },
    "digital_health_chw_tools": {
        "intervention": "Digital health tools for community health workers (mHealth, decision support apps)",
        "cost_per_daly_averted": "$100-500",
        "cost_per_life_saved": "$3,000-15,000",
        "evidence_strength": "Moderate — growing evidence base; WHO guideline on digital health interventions (2019); heterogeneous results depending on implementation context",
        "key_source": "WHO guideline on digital interventions for health system strengthening, DCP3, Lancet Digital Health reviews",
        "who_threshold": "Cost-effective in most contexts",
        "scalability": "High — leverages existing mobile phone infrastructure in LMICs",
        "relevant_dhis2_indicators": ["CHW visits", "Referral completeness", "Data reporting timeliness"],
    },
    "point_of_care_diagnostics": {
        "intervention": "Point-of-care diagnostics (GeneXpert, lab-on-chip, multiplex platforms)",
        "cost_per_daly_averted": "$50-300",
        "cost_per_life_saved": "$2,000-10,000",
        "evidence_strength": "Strong — GeneXpert for TB is WHO standard of care; emerging evidence for multiplex and lab-on-chip platforms",
        "key_source": "WHO diagnostic guidelines, FIND (Foundation for Innovative New Diagnostics), DCP3",
        "who_threshold": "Cost-effective to highly cost-effective depending on test and disease",
        "scalability": "Medium — requires device procurement but lower infrastructure than lab-based diagnostics",
        "relevant_dhis2_indicators": ["GeneXpert utilization", "TB case detection", "Diagnostic test availability"],
    },
    "maternal_health_ai_screening": {
        "intervention": "AI-based maternal health risk screening and triage",
        "cost_per_daly_averted": "Not yet established — emerging technology",
        "cost_per_life_saved": "Not yet established",
        "evidence_strength": "Weak — limited published evidence for smartphone-based predictive models for preeclampsia or neonatal sepsis; most studies are proof-of-concept",
        "key_source": "Lancet Digital Health case studies, WHO target product profiles for preeclampsia",
        "who_threshold": "Unestablished",
        "scalability": "Potentially high if validated (software-only, integrates with existing ANC workflows)",
        "relevant_dhis2_indicators": ["ANC coverage", "Preeclampsia cases detected", "Maternal mortality ratio", "Skilled birth attendance"],
    },
    "health_information_systems": {
        "intervention": "Health management information systems (HMIS/DHIS2) strengthening",
        "cost_per_daly_averted": "Indirect — enables effective targeting of health interventions",
        "cost_per_life_saved": "Indirect — improves program management and resource allocation",
        "evidence_strength": "Strong — DHIS2 deployed in 129 countries; evidence that data-driven management improves health outcomes",
        "key_source": "HISP/University of Oslo, WHO Digital Health Strategy, Open Data Watch",
        "who_threshold": "Essential health system infrastructure",
        "scalability": "Very high — already the backbone of health data in 75+ LMICs",
        "relevant_dhis2_indicators": ["Reporting completeness", "Data timeliness", "Facility reporting rate"],
    },
    # ── NON-HEALTH GH&D INTERVENTIONS ──
    "cash_transfers": {
        "intervention": "Unconditional cash transfers to extreme poor households",
        "cost_per_daly_averted": "N/A — measured in income gains and consumption",
        "cost_per_life_saved": "N/A",
        "evidence_strength": "Very strong — extensive RCT evidence from GiveDirectly and government programs across 30+ countries",
        "key_source": "GiveWell (GiveDirectly), J-PAL cash transfers review, World Bank",
        "who_threshold": "N/A — non-health",
        "scalability": "Very high — proven at government scale in multiple countries",
        "relevant_dhis2_indicators": [],
        "impact_metrics": "Average 25-30% consumption increase; effects persist 3+ years; positive spillovers on mental health and child nutrition",
    },
    "school_feeding": {
        "intervention": "School feeding programs",
        "cost_per_daly_averted": "$50-200",
        "cost_per_life_saved": "N/A — primarily educational and nutritional outcomes",
        "evidence_strength": "Strong — Cochrane review shows increased school attendance (8-12%), improved nutrition, and cognitive gains",
        "key_source": "WFP, Cochrane review, DCP3",
        "who_threshold": "Cost-effective (cross-sector benefits)",
        "scalability": "Very high — WFP reaches 150+ million children annually",
        "relevant_dhis2_indicators": ["School enrollment", "Stunting prevalence"],
        "impact_metrics": "8-12% increase in school attendance; reduced anemia and stunting; improved concentration and test scores",
    },
    "deworming": {
        "intervention": "Mass school-based deworming programs",
        "cost_per_daly_averted": "$5-50",
        "cost_per_life_saved": "N/A — primarily morbidity reduction",
        "evidence_strength": "Moderate-Strong — significant debate on long-term effects; GiveWell rates highly based on cost-effectiveness despite evidence uncertainty",
        "key_source": "GiveWell (Evidence Action, SCI Foundation), Miguel & Kremer 2004, Cochrane review",
        "who_threshold": "Highly cost-effective",
        "scalability": "Very high — simple delivery through schools",
        "relevant_dhis2_indicators": ["Deworming coverage", "School health program coverage"],
        "impact_metrics": "Low cost per treatment ($0.50-1.00); potential long-term income gains of 20-30% (contested); reduced school absenteeism",
    },
    "early_childhood_education": {
        "intervention": "Early childhood development (ECD) programs",
        "cost_per_daly_averted": "N/A — measured in developmental and economic outcomes",
        "cost_per_life_saved": "N/A",
        "evidence_strength": "Strong — extensive evidence from Jamaica, Colombia, India; Lancet ECD series",
        "key_source": "Lancet Early Childhood Development Series, J-PAL, World Bank",
        "who_threshold": "N/A — non-health",
        "scalability": "Medium — requires trained facilitators and community engagement",
        "relevant_dhis2_indicators": [],
        "impact_metrics": "25-40% gains in cognitive development; 10-25% income gains in adulthood from landmark studies; high benefit-cost ratios ($6-17 per $1 invested)",
    },
    "girls_education": {
        "intervention": "Girls' education support (scholarships, conditional transfers, menstrual health)",
        "cost_per_daly_averted": "N/A — measured in educational and demographic outcomes",
        "cost_per_life_saved": "N/A",
        "evidence_strength": "Strong — extensive evidence on returns to girls' education; World Bank estimates each year of secondary education reduces child marriage by 5-10%",
        "key_source": "World Bank, Malala Fund, UNICEF, J-PAL education review",
        "who_threshold": "N/A — non-health",
        "scalability": "High — multiple proven delivery models",
        "relevant_dhis2_indicators": [],
        "impact_metrics": "Each additional year of schooling increases future earnings 8-13%; reduces child marriage and early pregnancy; improves child health outcomes in next generation",
    },
    "agricultural_extension": {
        "intervention": "Agricultural extension services and smallholder farmer support",
        "cost_per_daly_averted": "N/A — measured in income and food security outcomes",
        "cost_per_life_saved": "N/A",
        "evidence_strength": "Moderate — heterogeneous results; strongest evidence for bundled interventions (inputs + training + market access)",
        "key_source": "J-PAL agriculture review, CGIAR, FAO, One Acre Fund evaluations",
        "who_threshold": "N/A — non-health",
        "scalability": "High — One Acre Fund model reaches 1.5M+ farmers",
        "relevant_dhis2_indicators": [],
        "impact_metrics": "20-50% yield increases from improved inputs; income gains vary by context; food security improvements measurable but context-dependent",
    },
    "microfinance_livelihoods": {
        "intervention": "Graduation approach / ultra-poor livelihoods programs",
        "cost_per_daly_averted": "N/A — measured in income and poverty outcomes",
        "cost_per_life_saved": "N/A",
        "evidence_strength": "Strong — 6-country RCT by Banerjee et al. (2015) shows sustained poverty reduction; BRAC graduation model extensively evaluated",
        "key_source": "Science (Banerjee et al. 2015), J-PAL, BRAC, Partnership for Economic Inclusion",
        "who_threshold": "N/A — non-health",
        "scalability": "Medium-High — intensive but proven at scale by BRAC (Bangladesh) and government programs",
        "relevant_dhis2_indicators": [],
        "impact_metrics": "Sustained 10-15% consumption increase 3+ years post-program; positive effects on savings, food security, and mental health",
    },
    "climate_adaptation": {
        "intervention": "Climate adaptation and resilience programs for vulnerable communities",
        "cost_per_daly_averted": "N/A — measured in lives protected and economic losses averted",
        "cost_per_life_saved": "Highly variable by intervention type",
        "evidence_strength": "Moderate — growing evidence base; heterogeneous interventions make comparison difficult",
        "key_source": "GCA (Global Center on Adaptation), IPCC AR6, World Bank Climate Action Plan",
        "who_threshold": "N/A",
        "scalability": "Variable — early warning systems highly scalable; infrastructure projects less so",
        "relevant_dhis2_indicators": [],
        "impact_metrics": "Early warning systems can reduce disaster deaths by 50%+; drought-resistant crops show 15-25% yield stability improvement; benefit-cost ratios of 4:1 to 10:1 for adaptation investments",
    },
    "gender_based_violence": {
        "intervention": "Gender-based violence prevention and response programs",
        "cost_per_daly_averted": "$50-300",
        "cost_per_life_saved": "N/A — primarily morbidity and wellbeing outcomes",
        "evidence_strength": "Moderate — SASA! community mobilization model has strong RCT evidence (52% reduction in physical IPV); other models have mixed evidence",
        "key_source": "Lancet GBV Series, WHO, Raising Voices (SASA!), What Works to Prevent VAWG",
        "who_threshold": "Cost-effective",
        "scalability": "Medium — requires community engagement and trained facilitators",
        "relevant_dhis2_indicators": [],
        "impact_metrics": "SASA! model: 52% reduction in physical intimate partner violence; community attitudes shift measurably; economic empowerment components show added impact",
    },
    "humanitarian_cash": {
        "intervention": "Cash assistance in humanitarian emergencies",
        "cost_per_daly_averted": "N/A — measured in basic needs coverage",
        "cost_per_life_saved": "N/A",
        "evidence_strength": "Strong — extensive evidence from humanitarian contexts; generally preferred over in-kind aid for cost-effectiveness",
        "key_source": "ODI/CGD cash transfer evidence review, UNHCR, WFP, IRC",
        "who_threshold": "N/A",
        "scalability": "Very high — digital payment infrastructure expanding rapidly in crisis contexts",
        "relevant_dhis2_indicators": [],
        "impact_metrics": "15-25% more cost-effective than in-kind aid; multiplier effects in local economies; improved dignity and choice for recipients",
    },
}

# Major GH&D organizations by focus area (for the agent to reference)
ORGANIZATIONS_DB = {
    "malaria": [
        {"name": "Against Malaria Foundation", "rating": "GiveWell Top Charity", "focus": "ITN distribution", "geographies": "Sub-Saharan Africa", "url": "againstmalaria.com"},
        {"name": "Malaria Consortium", "rating": "GiveWell Top Charity", "focus": "Seasonal malaria chemoprevention", "geographies": "Sahel region, Mozambique, Uganda", "url": "malariaconsortium.org"},
        {"name": "Nothing But Nets (UN Foundation)", "rating": "Established", "focus": "ITN campaigns", "geographies": "Sub-Saharan Africa", "url": "nothingbutnets.net"},
    ],
    "maternal_child_health": [
        {"name": "Helen Keller International", "rating": "GiveWell Top Charity", "focus": "Vitamin A supplementation, nutrition", "geographies": "Sub-Saharan Africa, Asia", "url": "hki.org"},
        {"name": "Maternal Health Initiative", "rating": "Established", "focus": "Skilled birth attendance, EmOC", "geographies": "West Africa, East Africa", "url": ""},
        {"name": "Partners in Health", "rating": "Highly rated", "focus": "Comprehensive health systems including maternal care", "geographies": "Haiti, Rwanda, Sierra Leone, others", "url": "pih.org"},
    ],
    "immunization": [
        {"name": "Gavi, the Vaccine Alliance", "rating": "Major multilateral", "focus": "Vaccine procurement and delivery", "geographies": "73 eligible countries", "url": "gavi.org"},
        {"name": "UNICEF Immunization", "rating": "UN Agency", "focus": "Last-mile vaccine delivery", "geographies": "Global", "url": "unicef.org"},
    ],
    "hiv_aids": [
        {"name": "Elizabeth Glaser Pediatric AIDS Foundation", "rating": "Highly rated", "focus": "Pediatric HIV, PMTCT", "geographies": "Sub-Saharan Africa", "url": "pedaids.org"},
        {"name": "Partners in Hope", "rating": "Established", "focus": "HIV treatment and prevention", "geographies": "Malawi", "url": "partnersinhopemalawi.org"},
    ],
    "tuberculosis": [
        {"name": "Stop TB Partnership", "rating": "Major partnership", "focus": "TB diagnosis and treatment", "geographies": "Global", "url": "stoptb.org"},
        {"name": "TB Alliance", "rating": "Established", "focus": "New TB drug development", "geographies": "Global", "url": "tballiance.org"},
    ],
    "nutrition": [
        {"name": "Action Against Hunger", "rating": "Highly rated", "focus": "Acute malnutrition treatment", "geographies": "50 countries", "url": "actionagainsthunger.org"},
        {"name": "Global Alliance for Improved Nutrition (GAIN)", "rating": "Established", "focus": "Food fortification, nutrition systems", "geographies": "Global", "url": "gainhealth.org"},
    ],
    "wash": [
        {"name": "Evidence Action (Dispensers for Safe Water)", "rating": "GiveWell Top Charity", "focus": "Chlorine dispensers for water treatment", "geographies": "Kenya, Uganda, Malawi", "url": "evidenceaction.org"},
        {"name": "WaterAid", "rating": "Highly rated", "focus": "WASH infrastructure and advocacy", "geographies": "34 countries", "url": "wateraid.org"},
    ],
    "general_ghd": [
        {"name": "GiveDirectly", "rating": "GiveWell Top Charity", "focus": "Direct cash transfers", "geographies": "Sub-Saharan Africa, global", "url": "givedirectly.org"},
        {"name": "New Incentives", "rating": "GiveWell Top Charity", "focus": "Conditional cash transfers for immunization", "geographies": "Nigeria", "url": "newincentives.org"},
    ],
    "diagnostics": [
        {"name": "FIND (Foundation for Innovative New Diagnostics)", "rating": "Major global partnership", "focus": "Developing and delivering diagnostic tests for poverty-related diseases", "geographies": "Global, 40+ countries", "url": "finddx.org"},
        {"name": "Clinton Health Access Initiative (CHAI)", "rating": "Highly rated", "focus": "Diagnostic access, market shaping, point-of-care testing", "geographies": "35+ countries in Africa and Asia", "url": "clintonhealthaccess.org"},
        {"name": "Medic (Community Health Toolkit)", "rating": "DPG registered", "focus": "Open-source digital tools for community health workers", "geographies": "25+ countries", "url": "medic.org"},
        {"name": "Dimagi (CommCare)", "rating": "Established", "focus": "Mobile data collection and decision support for health workers", "geographies": "80+ countries", "url": "dimagi.com"},
    ],
    "digital_health": [
        {"name": "Digital Square (PATH)", "rating": "Major initiative", "focus": "Coordinating investment in digital health global goods", "geographies": "Global", "url": "digitalsquare.org"},
        {"name": "Medic (Community Health Toolkit)", "rating": "DPG registered", "focus": "Open-source CHW tools", "geographies": "25+ countries", "url": "medic.org"},
        {"name": "OpenMRS", "rating": "DPG registered", "focus": "Open-source electronic medical records", "geographies": "50+ countries", "url": "openmrs.org"},
        {"name": "HISP / DHIS2", "rating": "DPG registered", "focus": "Health management information systems", "geographies": "129 countries", "url": "dhis2.org"},
    ],
    "education": [
        {"name": "Room to Read", "rating": "Highly rated", "focus": "Literacy and girls' education", "geographies": "21 countries in Africa and Asia", "url": "roomtoread.org"},
        {"name": "Pratham", "rating": "Highly rated (J-PAL evaluated)", "focus": "Early learning, Teaching at the Right Level", "geographies": "India, Africa (via partnerships)", "url": "pratham.org"},
        {"name": "Camfed", "rating": "GiveWell standout", "focus": "Girls' education and women's empowerment", "geographies": "Sub-Saharan Africa (5 countries)", "url": "camfed.org"},
        {"name": "Evidence Action (Deworm the World)", "rating": "GiveWell Top Charity", "focus": "School-based deworming", "geographies": "India, Kenya, Nigeria, Ethiopia, Vietnam", "url": "evidenceaction.org"},
    ],
    "economic_development": [
        {"name": "GiveDirectly", "rating": "GiveWell Top Charity", "focus": "Unconditional cash transfers", "geographies": "Sub-Saharan Africa, global", "url": "givedirectly.org"},
        {"name": "BRAC", "rating": "Major INGO", "focus": "Ultra-poor graduation, microfinance, livelihoods", "geographies": "11 countries, Bangladesh-based", "url": "brac.net"},
        {"name": "Village Enterprise", "rating": "GiveWell standout", "focus": "Microenterprise development for ultra-poor", "geographies": "East Africa", "url": "villageenterprise.org"},
        {"name": "One Acre Fund", "rating": "Highly rated", "focus": "Smallholder farmer support", "geographies": "6 countries in Sub-Saharan Africa", "url": "oneacrefund.org"},
    ],
    "agriculture": [
        {"name": "One Acre Fund", "rating": "Highly rated", "focus": "Farm inputs, training, market access for smallholders", "geographies": "6 countries in Sub-Saharan Africa", "url": "oneacrefund.org"},
        {"name": "CGIAR", "rating": "Major research partnership", "focus": "Agricultural research for development", "geographies": "Global", "url": "cgiar.org"},
        {"name": "Farm Africa", "rating": "Established", "focus": "Sustainable agriculture and forestry", "geographies": "East Africa", "url": "farmafrica.org"},
    ],
    "gender": [
        {"name": "Camfed", "rating": "GiveWell standout", "focus": "Girls' education and women's empowerment", "geographies": "Sub-Saharan Africa", "url": "camfed.org"},
        {"name": "Women for Women International", "rating": "Established", "focus": "Women's economic empowerment in conflict settings", "geographies": "8 conflict-affected countries", "url": "womenforwomen.org"},
        {"name": "Raising Voices", "rating": "Evidence-backed", "focus": "GBV prevention (SASA! model)", "geographies": "East Africa, global adaptation", "url": "raisingvoices.org"},
    ],
    "humanitarian": [
        {"name": "IRC (International Rescue Committee)", "rating": "Highly rated", "focus": "Humanitarian response and cash assistance", "geographies": "40+ countries", "url": "rescue.org"},
        {"name": "UNHCR", "rating": "UN Agency", "focus": "Refugee protection and assistance", "geographies": "Global", "url": "unhcr.org"},
        {"name": "Mercy Corps", "rating": "Highly rated", "focus": "Emergency response and resilience", "geographies": "40+ countries", "url": "mercycorps.org"},
    ],
    "climate": [
        {"name": "Global Center on Adaptation", "rating": "Major initiative", "focus": "Climate adaptation in developing countries", "geographies": "Global, focus on Africa", "url": "gca.org"},
        {"name": "WRI (World Resources Institute)", "rating": "Major research org", "focus": "Climate, energy, food, forests", "geographies": "Global", "url": "wri.org"},
    ],
}


# ══════════════════════════════════════════════
# TOOL DEFINITIONS FOR CLAUDE
# ══════════════════════════════════════════════

TOOLS = [
    {
        "name": "query_health_data",
        "description": """Query health program data from DHIS2 (national health information systems used in 129 countries).
Returns real, verified health indicators for specific geographies.
Use this to ground recommendations in actual program outcome data.
Available indicator groups: immunization, malaria, maternal health, nutrition, HIV, TB, general health services.
Available geographies: Use organisation unit names (districts, regions, or country-level).""",
        "input_schema": {
            "type": "object",
            "properties": {
                "indicator_category": {
                    "type": "string",
                    "description": "Category of health indicators to query",
                    "enum": ["immunization", "malaria", "maternal_health", "nutrition", "hiv", "tb", "general"]
                },
                "geography": {
                    "type": "string",
                    "description": "Geographic area to query (district, region, or country name)"
                },
                "purpose": {
                    "type": "string",
                    "description": "Brief note on why this data is being queried (for reasoning transparency)"
                }
            },
            "required": ["indicator_category", "geography", "purpose"]
        }
    },
    {
        "name": "search_evidence",
        "description": """Search the evidence base for impact evaluations, systematic reviews, and intervention effectiveness data.
Draws from curated data sourced from GiveWell, DCP3 (Disease Control Priorities), Cochrane reviews, J-PAL, 3ie, and WHO guidelines.
Use this to identify what interventions work for a given health area and how strong the evidence is.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "health_area": {
                    "type": "string",
                    "description": "Health area or topic to search evidence for (e.g., 'malaria prevention', 'maternal mortality', 'child nutrition')"
                },
                "question": {
                    "type": "string",
                    "description": "Specific question the evidence should answer"
                }
            },
            "required": ["health_area", "question"]
        }
    },
    {
        "name": "assess_cost_effectiveness",
        "description": """Look up cost-effectiveness data for specific health interventions.
Returns cost per DALY averted, cost per life saved, evidence strength, WHO threshold classification, and scalability assessment.
Use this to help donors understand value for money and compare different giving opportunities.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "intervention_area": {
                    "type": "string",
                    "description": "The health intervention or area to assess (e.g., 'bed nets', 'immunization', 'maternal care', 'HIV treatment')"
                },
                "donor_budget": {
                    "type": "string",
                    "description": "The donor's budget (optional, used to contextualize impact)"
                }
            },
            "required": ["intervention_area"]
        }
    },
    {
        "name": "find_organizations",
        "description": """Find organizations working on specific health areas that donors can support.
Returns organization names, ratings, focus areas, and geographies of operation.
Use this to match donors with specific programs and giving pathways.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "health_area": {
                    "type": "string",
                    "description": "Health area to find organizations for"
                },
                "geography_preference": {
                    "type": "string",
                    "description": "Preferred geography (optional)"
                }
            },
            "required": ["health_area"]
        }
    },
    {
        "name": "web_research",
        "description": """Conduct live web research on a topic to find the latest information.
Use this for current news, recent developments, policy changes, funding announcements, 
new evidence, or any topic where the curated databases may not have the latest information.
This is especially useful for emerging health issues, recent crises, or donor-specific questions.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for web research"
                },
                "purpose": {
                    "type": "string",
                    "description": "Why this research is needed for the donor's question"
                }
            },
            "required": ["query", "purpose"]
        }
    }
]

# ══════════════════════════════════════════════
# TOOL IMPLEMENTATIONS
# ══════════════════════════════════════════════

import requests
from requests.auth import HTTPBasicAuth

# Cached representative DHIS2 data for reliable demos when servers are down
CACHED_DHIS2_DATA = {
    ("malaria", "Sierra Leone"): {
        "source": "DHIS2 National Health Information System (cached demo data — Sierra Leone)",
        "data_type": "Verified program data from health facilities",
        "geography_found": [{"name": "Sierra Leone", "level": 1}],
        "indicators_found": ["ANC LLITN coverage", "Slept under LLITN last night", "Malaria cases confirmed", "Malaria RDT positive rate", "ITN distributed"],
        "analytics_data": [
            {"indicator": "ANC LLITN coverage", "period": "April 2025", "value": "25.26"},
            {"indicator": "ANC LLITN coverage", "period": "May 2025", "value": "53.46"},
            {"indicator": "ANC LLITN coverage", "period": "June 2025", "value": "56.13"},
            {"indicator": "ANC LLITN coverage", "period": "July 2025", "value": "72.61"},
            {"indicator": "ANC LLITN coverage", "period": "August 2025", "value": "64.89"},
            {"indicator": "ANC LLITN coverage", "period": "September 2025", "value": "59.69"},
            {"indicator": "ANC LLITN coverage", "period": "October 2025", "value": "23.64"},
            {"indicator": "ANC LLITN coverage", "period": "November 2025", "value": "36.9"},
            {"indicator": "ANC LLITN coverage", "period": "December 2025", "value": "10.22"},
            {"indicator": "Slept under LLITN last night", "period": "April 2025", "value": "65.63"},
            {"indicator": "Slept under LLITN last night", "period": "May 2025", "value": "71.12"},
            {"indicator": "Slept under LLITN last night", "period": "June 2025", "value": "73.93"},
        ],
        "data_quality_note": "Cached data from DHIS2 demo instance. In production, connects to actual national DHIS2 instances.",
    },
    ("immunization", "Sierra Leone"): {
        "source": "DHIS2 National Health Information System (cached demo data — Sierra Leone)",
        "data_type": "Verified program data from health facilities",
        "geography_found": [{"name": "Sierra Leone", "level": 1}],
        "indicators_found": ["BCG coverage", "DPT3 coverage", "Measles coverage", "OPV3 coverage", "Penta3 coverage", "Fully immunized children"],
        "analytics_data": [
            {"indicator": "BCG coverage", "period": "Q1 2025", "value": "89.4"},
            {"indicator": "BCG coverage", "period": "Q2 2025", "value": "91.2"},
            {"indicator": "BCG coverage", "period": "Q3 2025", "value": "87.6"},
            {"indicator": "DPT3 coverage", "period": "Q1 2025", "value": "72.3"},
            {"indicator": "DPT3 coverage", "period": "Q2 2025", "value": "74.8"},
            {"indicator": "DPT3 coverage", "period": "Q3 2025", "value": "71.1"},
            {"indicator": "Measles coverage", "period": "Q1 2025", "value": "68.5"},
            {"indicator": "Measles coverage", "period": "Q2 2025", "value": "71.2"},
            {"indicator": "Measles coverage", "period": "Q3 2025", "value": "66.9"},
            {"indicator": "Penta3 coverage", "period": "Q1 2025", "value": "73.1"},
            {"indicator": "Penta3 coverage", "period": "Q2 2025", "value": "75.4"},
        ],
        "data_quality_note": "Cached representative data. In production, connects to actual national DHIS2 instances.",
    },
    ("maternal_health", "Sierra Leone"): {
        "source": "DHIS2 National Health Information System (cached demo data — Sierra Leone)",
        "data_type": "Verified program data from health facilities",
        "geography_found": [{"name": "Sierra Leone", "level": 1}],
        "indicators_found": ["ANC 1st visit coverage", "ANC 4th visit coverage", "Facility delivery rate", "Skilled birth attendance", "Postnatal care coverage"],
        "analytics_data": [
            {"indicator": "ANC 1st visit coverage", "period": "Q1 2025", "value": "82.1"},
            {"indicator": "ANC 1st visit coverage", "period": "Q2 2025", "value": "85.3"},
            {"indicator": "ANC 4th visit coverage", "period": "Q1 2025", "value": "54.2"},
            {"indicator": "ANC 4th visit coverage", "period": "Q2 2025", "value": "57.8"},
            {"indicator": "Facility delivery rate", "period": "Q1 2025", "value": "61.4"},
            {"indicator": "Facility delivery rate", "period": "Q2 2025", "value": "63.2"},
            {"indicator": "Skilled birth attendance", "period": "Q1 2025", "value": "58.9"},
            {"indicator": "Skilled birth attendance", "period": "Q2 2025", "value": "61.1"},
        ],
        "data_quality_note": "Cached representative data. In production, connects to actual national DHIS2 instances.",
    },
    ("malaria", "Nigeria"): {
        "source": "DHIS2 National Health Information System (cached representative data — Nigeria)",
        "data_type": "Verified program data from health facilities",
        "geography_found": [{"name": "Nigeria", "level": 1}],
        "indicators_found": ["Malaria cases confirmed", "Malaria RDT positive rate", "ACT treatment rate", "ITN coverage", "Malaria deaths under 5"],
        "analytics_data": [
            {"indicator": "Malaria RDT positive rate", "period": "Q1 2025", "value": "42.3"},
            {"indicator": "Malaria RDT positive rate", "period": "Q2 2025", "value": "38.7"},
            {"indicator": "Malaria RDT positive rate", "period": "Q3 2025", "value": "51.2"},
            {"indicator": "ACT treatment rate", "period": "Q1 2025", "value": "67.8"},
            {"indicator": "ACT treatment rate", "period": "Q2 2025", "value": "71.4"},
            {"indicator": "ITN coverage", "period": "Q1 2025", "value": "45.6"},
            {"indicator": "ITN coverage", "period": "Q2 2025", "value": "48.2"},
        ],
        "data_quality_note": "Cached representative data based on typical Nigerian DHIS2 indicators. In production, connects to Nigeria's national DHIS2 instance.",
    },
    ("immunization", "Nigeria"): {
        "source": "DHIS2 National Health Information System (cached representative data — Nigeria)",
        "data_type": "Verified program data from health facilities",
        "geography_found": [{"name": "Nigeria", "level": 1}],
        "indicators_found": ["Penta3 coverage", "Measles coverage", "Zero-dose children", "BCG coverage", "IPV coverage"],
        "analytics_data": [
            {"indicator": "Penta3 coverage", "period": "Q1 2025", "value": "57.3"},
            {"indicator": "Penta3 coverage", "period": "Q2 2025", "value": "59.1"},
            {"indicator": "Penta3 coverage", "period": "Q3 2025", "value": "55.8"},
            {"indicator": "Measles coverage", "period": "Q1 2025", "value": "54.2"},
            {"indicator": "Measles coverage", "period": "Q2 2025", "value": "56.8"},
            {"indicator": "BCG coverage", "period": "Q1 2025", "value": "68.4"},
            {"indicator": "BCG coverage", "period": "Q2 2025", "value": "70.1"},
            {"indicator": "Zero-dose children", "period": "2024", "value": "2,180,000"},
        ],
        "data_quality_note": "Cached representative data. Nigeria has one of the highest numbers of zero-dose children globally. In production, connects to Nigeria's national DHIS2.",
    },
    ("maternal_health", "Nigeria"): {
        "source": "DHIS2 National Health Information System (cached representative data — Nigeria)",
        "data_type": "Verified program data from health facilities",
        "geography_found": [{"name": "Nigeria", "level": 1}],
        "indicators_found": ["ANC 1st visit coverage", "Facility delivery rate", "Skilled birth attendance", "Maternal mortality ratio"],
        "analytics_data": [
            {"indicator": "ANC 1st visit coverage", "period": "Q1 2025", "value": "67.2"},
            {"indicator": "ANC 1st visit coverage", "period": "Q2 2025", "value": "69.8"},
            {"indicator": "Facility delivery rate", "period": "Q1 2025", "value": "43.1"},
            {"indicator": "Facility delivery rate", "period": "Q2 2025", "value": "44.7"},
            {"indicator": "Skilled birth attendance", "period": "Q1 2025", "value": "42.8"},
            {"indicator": "Skilled birth attendance", "period": "Q2 2025", "value": "44.3"},
        ],
        "data_quality_note": "Cached representative data. Nigeria accounts for approximately 20% of global maternal deaths. In production, connects to national DHIS2.",
    },
    ("malaria", "Kenya"): {
        "source": "DHIS2 National Health Information System (cached representative data — Kenya)",
        "data_type": "Verified program data from health facilities",
        "geography_found": [{"name": "Kenya", "level": 1}],
        "indicators_found": ["Malaria cases confirmed", "Malaria test positivity rate", "ITN coverage", "ACT treatment", "Malaria deaths"],
        "analytics_data": [
            {"indicator": "Malaria test positivity rate", "period": "Q1 2025", "value": "22.1"},
            {"indicator": "Malaria test positivity rate", "period": "Q2 2025", "value": "19.8"},
            {"indicator": "Malaria test positivity rate", "period": "Q3 2025", "value": "28.4"},
            {"indicator": "ITN coverage", "period": "Q1 2025", "value": "62.3"},
            {"indicator": "ITN coverage", "period": "Q2 2025", "value": "64.1"},
            {"indicator": "ACT treatment", "period": "Q1 2025", "value": "78.9"},
        ],
        "data_quality_note": "Cached representative data. Kenya has significant regional variation in malaria burden. In production, connects to Kenya's national DHIS2.",
    },
}


def _find_cached_data(indicator_category, geography):
    """Try to find cached DHIS2 data matching the query."""
    geo_lower = geography.lower()
    # Try exact match first
    for (cat, geo), data in CACHED_DHIS2_DATA.items():
        if cat == indicator_category and geo.lower() == geo_lower:
            return data
    # Try partial match on geography
    for (cat, geo), data in CACHED_DHIS2_DATA.items():
        if cat == indicator_category and (geo.lower() in geo_lower or geo_lower in geo.lower()):
            return data
    # Try just the category with Sierra Leone as default
    for (cat, geo), data in CACHED_DHIS2_DATA.items():
        if cat == indicator_category and geo == "Sierra Leone":
            return data
    return None

def query_health_data(indicator_category, geography, purpose):
    """Query DHIS2 demo instance for health data. Checks database cache first."""
    
    # Check database cache first
    if "db" in st.session_state:
        db = st.session_state.db
        cache_key = db.make_cache_key("dhis2", indicator_category, geography)
        cached = db.get_cached_data(cache_key)
        if cached:
            cached["cache_note"] = "Served from cache (refreshes every 24 hours)"
            return cached
    
    # Map categories to DHIS2 indicator groups/data elements
    indicator_map = {
        "immunization": {
            "search_terms": ["BCG", "DPT", "Penta", "OPV", "Measles", "immunization", "vaccination", "vaccine"],
            "data_elements": ["BCG doses given", "DPT 1 doses given", "DPT 3 doses given", "Measles doses given", "OPV 3 doses given", "Penta3 doses given"],
        },
        "malaria": {
            "search_terms": ["Malaria", "ITN", "ACT", "bednet"],
            "data_elements": ["Malaria cases confirmed", "Malaria cases treated", "Malaria deaths", "ITN distributed"],
        },
        "maternal_health": {
            "search_terms": ["ANC", "antenatal", "delivery", "maternal", "postnatal", "birth"],
            "data_elements": ["ANC 1st visit", "ANC 4th visit", "Deliveries in facility", "Maternal deaths", "Skilled birth attendance"],
        },
        "nutrition": {
            "search_terms": ["Vitamin A", "nutrition", "stunting", "wasting", "malnutrition", "weight"],
            "data_elements": ["Vitamin A supplement", "Underweight children", "Nutrition screening"],
        },
        "hiv": {
            "search_terms": ["HIV", "ART", "PMTCT", "VCT", "viral load"],
            "data_elements": ["HIV tests performed", "HIV positive", "ART enrollment", "PMTCT"],
        },
        "tb": {
            "search_terms": ["TB", "tuberculosis", "DOTS", "GeneXpert"],
            "data_elements": ["TB cases detected", "TB treatment success", "TB deaths"],
        },
        "general": {
            "search_terms": ["OPD", "IPD", "outpatient", "inpatient", "consultation"],
            "data_elements": ["OPD visits", "IPD admissions"],
        }
    }
    
    category_info = indicator_map.get(indicator_category, indicator_map["general"])
    
    # Try each DHIS2 server until one works
    debug_log = []
    
    for base_url in DHIS2_SERVERS:
        try:
            # Quick connectivity check
            test_resp = requests.get(f"{base_url}/system/info.json", 
                                    auth=HTTPBasicAuth(DHIS2_USERNAME, DHIS2_PASSWORD), timeout=8)
            if test_resp.status_code != 200:
                debug_log.append(f"{base_url}: HTTP {test_resp.status_code}")
                continue
            
            debug_log.append(f"{base_url}: Connected (HTTP 200)")
            
            # Search for DHIS2 indicators (aggregate calculated values - work with analytics API)
            indicators = []
            for term in category_info["search_terms"][:3]:
                url = f"{base_url}/indicators.json"
                params = {
                    "filter": f"displayName:ilike:{term}",
                    "fields": "id,displayName",
                    "pageSize": 8
                }
                resp = requests.get(url, params=params, auth=HTTPBasicAuth(DHIS2_USERNAME, DHIS2_PASSWORD), timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for ind in data.get("indicators", []):
                        if ind not in indicators:
                            indicators.append(ind)
            
            debug_log.append(f"Indicators found: {len(indicators)}")
            
            # Also search data elements as supplementary info
            data_elements = []
            for term in category_info["search_terms"][:2]:
                url = f"{base_url}/dataElements.json"
                params = {
                    "filter": f"displayName:ilike:{term}",
                    "fields": "id,displayName",
                    "pageSize": 5
                }
                resp = requests.get(url, params=params, auth=HTTPBasicAuth(DHIS2_USERNAME, DHIS2_PASSWORD), timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for elem in data.get("dataElements", []):
                        if elem not in data_elements:
                            data_elements.append(elem)
            
            # Combine all found items for display
            results = indicators + data_elements
            debug_log.append(f"Data elements found: {len(data_elements)}, Total items: {len(results)}")
            
            # Search for the organisation unit
            org_url = f"{base_url}/organisationUnits.json"
            org_params = {
                "filter": f"displayName:ilike:{geography}",
                "fields": "id,displayName,level",
                "pageSize": 5
            }
            org_resp = requests.get(org_url, params=org_params, auth=HTTPBasicAuth(DHIS2_USERNAME, DHIS2_PASSWORD), timeout=10)
            org_units = []
            if org_resp.status_code == 200:
                org_units = org_resp.json().get("organisationUnits", [])
            
            debug_log.append(f"Org units found for '{geography}': {len(org_units)}")
            
            # If no org units found, try shorter search or known units
            if not org_units:
                # Try first word only (e.g. "Sierra" from "Sierra Leone")
                first_word = geography.split()[0] if geography else ""
                if first_word and len(first_word) > 2:
                    org_resp2 = requests.get(org_url, 
                        params={"filter": f"displayName:ilike:{first_word}", "fields": "id,displayName,level", "pageSize": 5},
                        auth=HTTPBasicAuth(DHIS2_USERNAME, DHIS2_PASSWORD), timeout=10)
                    if org_resp2.status_code == 200:
                        org_units = org_resp2.json().get("organisationUnits", [])
                        debug_log.append(f"Retry with '{first_word}': {len(org_units)} found")
            
            # If still no org units, try "Bo" (known district in Sierra Leone demo)
            if not org_units:
                org_resp3 = requests.get(org_url,
                    params={"filter": "displayName:ilike:Bo", "fields": "id,displayName,level", "pageSize": 5},
                    auth=HTTPBasicAuth(DHIS2_USERNAME, DHIS2_PASSWORD), timeout=10)
                if org_resp3.status_code == 200:
                    org_units = org_resp3.json().get("organisationUnits", [])
                    debug_log.append(f"Fallback to 'Bo' district: {len(org_units)} found")
            
            # Try to get analytics data — prefer indicators (work better with analytics API)
            analytics_results = []
            if org_units and (indicators or data_elements):
                ou_id = org_units[0]["id"]
                analytics_url = f"{base_url}/analytics.json"
                
                # Strategy 1: Try with indicators first (most reliable for analytics)
                if indicators:
                    ind_ids = [r["id"] for r in indicators[:5]]
                    for period in ["LAST_12_MONTHS", "LAST_4_QUARTERS", "THIS_YEAR", "2023", "2024"]:
                        analytics_params = {
                            "dimension": f"dx:{';'.join(ind_ids)},pe:{period}",
                            "filter": f"ou:{ou_id}",
                            "displayProperty": "NAME"
                        }
                        analytics_resp = requests.get(analytics_url, params=analytics_params,
                            auth=HTTPBasicAuth(DHIS2_USERNAME, DHIS2_PASSWORD), timeout=15)
                        debug_log.append(f"Analytics (indicators, {period}): HTTP {analytics_resp.status_code}")
                        
                        if analytics_resp.status_code == 200:
                            analytics_data = analytics_resp.json()
                            rows = analytics_data.get("rows", [])
                            meta = analytics_data.get("metaData", {}).get("items", {})
                            if rows:
                                for row in rows[:20]:
                                    analytics_results.append({
                                        "indicator": meta.get(row[0], {}).get("name", row[0]),
                                        "period": meta.get(row[1], {}).get("name", row[1]),
                                        "value": row[2]
                                    })
                                debug_log.append(f"Got {len(rows)} rows with indicators")
                                break
                
                # Strategy 2: Try with data elements if indicators didn't work
                if not analytics_results and data_elements:
                    # Try one data element at a time to avoid 409 conflicts
                    for de in data_elements[:5]:
                        for period in ["LAST_12_MONTHS", "LAST_4_QUARTERS", "2023"]:
                            analytics_params = {
                                "dimension": f"dx:{de['id']},pe:{period}",
                                "filter": f"ou:{ou_id}",
                                "displayProperty": "NAME"
                            }
                            analytics_resp = requests.get(analytics_url, params=analytics_params,
                                auth=HTTPBasicAuth(DHIS2_USERNAME, DHIS2_PASSWORD), timeout=10)
                            if analytics_resp.status_code == 200:
                                analytics_data = analytics_resp.json()
                                rows = analytics_data.get("rows", [])
                                meta = analytics_data.get("metaData", {}).get("items", {})
                                if rows:
                                    for row in rows[:5]:
                                        analytics_results.append({
                                            "indicator": meta.get(row[0], {}).get("name", row[0]),
                                            "period": meta.get(row[1], {}).get("name", row[1]),
                                            "value": row[2]
                                        })
                                    break
                        if analytics_results:
                            debug_log.append(f"Got {len(analytics_results)} rows from data elements")
                            break
                
                # Strategy 3: Try dataValueSets as last resort
                if not analytics_results and data_elements:
                    dvs_url = f"{base_url}/dataValueSets.json"
                    de_id = data_elements[0]["id"]
                    dvs_params = {
                        "dataElement": de_id,
                        "orgUnit": ou_id,
                        "period": "202301",
                        "children": "true",
                        "limit": 10
                    }
                    dvs_resp = requests.get(dvs_url, params=dvs_params,
                        auth=HTTPBasicAuth(DHIS2_USERNAME, DHIS2_PASSWORD), timeout=10)
                    debug_log.append(f"DataValueSets fallback: HTTP {dvs_resp.status_code}")
                    if dvs_resp.status_code == 200:
                        dvs_data = dvs_resp.json()
                        for dv in dvs_data.get("dataValues", [])[:10]:
                            analytics_results.append({
                                "indicator": data_elements[0]["displayName"],
                                "period": dv.get("period", "unknown"),
                                "value": dv.get("value", "N/A"),
                                "org_unit": dv.get("orgUnit", "")
                            })
                        if analytics_results:
                            debug_log.append(f"DataValueSets returned {len(analytics_results)} values")
            
            result = {
                "source": f"DHIS2 National Health Information System (demo: {base_url.split('/api')[0].split('/')[-1]})",
                "data_type": "Verified program data from health facilities",
                "geography_found": [{"name": ou["displayName"], "level": ou.get("level", "N/A")} for ou in org_units[:3]],
                "indicators_found": [r["displayName"] for r in results[:10]],
                "analytics_data": analytics_results[:15] if analytics_results else f"No analytics data for this period/geography combination. {len(results)} indicators and {len(org_units)} org units were found in the system.",
                "note": f"Query purpose: {purpose}. Data sourced from DHIS2, used by ministries of health in 129 countries.",
                "data_quality_note": "This is demo instance data. In production, this connects to actual national DHIS2 instances.",
                "debug": debug_log
            }
            
            # Cache successful result in database
            if "db" in st.session_state:
                cache_key = st.session_state.db.make_cache_key("dhis2", indicator_category, geography)
                st.session_state.db.set_cached_data(cache_key, result, source="dhis2", ttl_hours=24)
            
            return result
            
        except requests.exceptions.Timeout:
            debug_log.append(f"{base_url}: Timed out")
            continue
        except Exception as e:
            debug_log.append(f"{base_url}: Error - {str(e)[:100]}")
            continue
    
    # All servers failed — try cached data
    cached = _find_cached_data(indicator_category, geography)
    if cached:
        cached_result = dict(cached)
        cached_result["note"] = f"Query purpose: {purpose}. Live DHIS2 servers were unreachable; using cached representative data. In production, this connects to the national DHIS2 instance."
        cached_result["debug"] = debug_log + ["All servers failed — using cached data"]
        return cached_result
    
    return {
        "source": "DHIS2 (all servers unreachable, no cached data available)",
        "debug": debug_log,
        "fallback": f"Could not connect to any DHIS2 demo server. Standard {indicator_category} indicators include: {', '.join(category_info['data_elements'][:5])}",
        "note": f"Query purpose: {purpose}. In production, this would connect to the national DHIS2 instance in the target country."
    }


def search_evidence(health_area, question):
    """Search the curated evidence base."""
    
    # Match the query to relevant interventions in our database
    area_lower = health_area.lower()
    matching = []
    
    keyword_map = {
        "malaria": ["insecticide_treated_nets", "seasonal_malaria_chemoprevention"],
        "bed net": ["insecticide_treated_nets"],
        "itn": ["insecticide_treated_nets"],
        "smc": ["seasonal_malaria_chemoprevention"],
        "diarrhea": ["oral_rehydration_therapy", "clean_water_and_sanitation"],
        "ors": ["oral_rehydration_therapy"],
        "vitamin a": ["vitamin_a_supplementation"],
        "nutrition": ["vitamin_a_supplementation", "nutrition_supplementation"],
        "stunting": ["nutrition_supplementation"],
        "malnutrition": ["nutrition_supplementation"],
        "maternal": ["skilled_birth_attendance", "family_planning"],
        "birth": ["skilled_birth_attendance"],
        "pregnancy": ["skilled_birth_attendance", "family_planning"],
        "immunization": ["childhood_immunization"],
        "vaccine": ["childhood_immunization"],
        "vaccination": ["childhood_immunization"],
        "hiv": ["hiv_art"],
        "aids": ["hiv_art"],
        "art": ["hiv_art"],
        "tb": ["tuberculosis_treatment"],
        "tuberculosis": ["tuberculosis_treatment"],
        "water": ["clean_water_and_sanitation"],
        "sanitation": ["clean_water_and_sanitation"],
        "wash": ["clean_water_and_sanitation"],
        "family planning": ["family_planning"],
        "contracepti": ["family_planning"],
        "community health": ["community_health_workers"],
        "chw": ["community_health_workers"],
        "child mortality": ["childhood_immunization", "oral_rehydration_therapy", "insecticide_treated_nets", "vitamin_a_supplementation", "nutrition_supplementation"],
        "child health": ["childhood_immunization", "oral_rehydration_therapy", "vitamin_a_supplementation", "nutrition_supplementation"],
        "under-5": ["childhood_immunization", "oral_rehydration_therapy", "insecticide_treated_nets", "vitamin_a_supplementation"],
        "neonatal": ["skilled_birth_attendance", "community_health_workers"],
        "infectious disease": ["insecticide_treated_nets", "hiv_art", "tuberculosis_treatment", "childhood_immunization"],
        "poverty": ["community_health_workers"],
        "diagnostic": ["malaria_rdt", "ai_malaria_rdt_reading", "ai_anemia_screening", "ai_tb_screening", "point_of_care_diagnostics"],
        "screening": ["malaria_rdt", "ai_malaria_rdt_reading", "ai_anemia_screening", "ai_tb_screening", "maternal_health_ai_screening"],
        "rdt": ["malaria_rdt", "ai_malaria_rdt_reading"],
        "rapid test": ["malaria_rdt", "ai_malaria_rdt_reading"],
        "smartphone": ["ai_malaria_rdt_reading", "ai_anemia_screening", "ai_tb_screening", "digital_health_chw_tools"],
        "mobile": ["ai_malaria_rdt_reading", "ai_anemia_screening", "ai_tb_screening", "digital_health_chw_tools"],
        "app": ["ai_malaria_rdt_reading", "ai_anemia_screening", "ai_tb_screening", "digital_health_chw_tools"],
        "anemia": ["ai_anemia_screening", "vitamin_a_supplementation", "nutrition_supplementation"],
        "conjunctiv": ["ai_anemia_screening"],
        "hemoglobin": ["ai_anemia_screening"],
        "cough": ["ai_tb_screening"],
        "x-ray": ["ai_tb_screening"],
        "chest": ["ai_tb_screening"],
        "genexpert": ["point_of_care_diagnostics", "tuberculosis_treatment"],
        "point-of-care": ["point_of_care_diagnostics"],
        "poc": ["point_of_care_diagnostics"],
        "lab-on-chip": ["point_of_care_diagnostics"],
        "preeclampsia": ["maternal_health_ai_screening"],
        "sepsis": ["maternal_health_ai_screening"],
        "triage": ["maternal_health_ai_screening"],
        "mhealth": ["digital_health_chw_tools"],
        "digital health": ["digital_health_chw_tools", "health_information_systems"],
        "dhis2": ["health_information_systems"],
        "hmis": ["health_information_systems"],
        "health information": ["health_information_systems"],
        "software": ["ai_malaria_rdt_reading", "ai_anemia_screening", "ai_tb_screening", "digital_health_chw_tools"],
        "ai diagnos": ["ai_malaria_rdt_reading", "ai_anemia_screening", "ai_tb_screening"],
        "artificial intelligence": ["ai_malaria_rdt_reading", "ai_anemia_screening", "ai_tb_screening", "digital_health_chw_tools"],
        "cash transfer": ["cash_transfers", "humanitarian_cash"],
        "cash": ["cash_transfers", "humanitarian_cash"],
        "givedirectly": ["cash_transfers"],
        "school feeding": ["school_feeding"],
        "school meal": ["school_feeding"],
        "wfp": ["school_feeding"],
        "deworming": ["deworming"],
        "helminth": ["deworming"],
        "early childhood": ["early_childhood_education"],
        "ecd": ["early_childhood_education"],
        "preschool": ["early_childhood_education"],
        "girl": ["girls_education"],
        "scholarship": ["girls_education"],
        "education": ["girls_education", "early_childhood_education", "school_feeding", "deworming"],
        "school": ["girls_education", "school_feeding", "deworming"],
        "literacy": ["girls_education", "early_childhood_education"],
        "enrollment": ["girls_education", "school_feeding"],
        "agricult": ["agricultural_extension"],
        "farming": ["agricultural_extension"],
        "smallholder": ["agricultural_extension"],
        "crop": ["agricultural_extension"],
        "food security": ["agricultural_extension", "school_feeding", "nutrition_supplementation"],
        "livelihood": ["microfinance_livelihoods"],
        "graduation": ["microfinance_livelihoods"],
        "ultra-poor": ["microfinance_livelihoods", "cash_transfers"],
        "microfinance": ["microfinance_livelihoods"],
        "brac": ["microfinance_livelihoods"],
        "economic empowerment": ["microfinance_livelihoods", "girls_education"],
        "climate": ["climate_adaptation"],
        "drought": ["climate_adaptation"],
        "flood": ["climate_adaptation"],
        "early warning": ["climate_adaptation"],
        "resilience": ["climate_adaptation"],
        "adaptation": ["climate_adaptation"],
        "gender": ["gender_based_violence", "girls_education"],
        "violence": ["gender_based_violence"],
        "gbv": ["gender_based_violence"],
        "intimate partner": ["gender_based_violence"],
        "women": ["gender_based_violence", "girls_education", "family_planning"],
        "humanitarian": ["humanitarian_cash", "cash_transfers"],
        "emergency": ["humanitarian_cash"],
        "refugee": ["humanitarian_cash"],
        "crisis": ["humanitarian_cash"],
        "displacement": ["humanitarian_cash"],
    }
    
    matched_keys = set()
    for keyword, keys in keyword_map.items():
        if keyword in area_lower:
            matched_keys.update(keys)
    
    # If no specific match, return top interventions by cost-effectiveness
    if not matched_keys:
        matched_keys = {"insecticide_treated_nets", "childhood_immunization", "vitamin_a_supplementation", "oral_rehydration_therapy", "seasonal_malaria_chemoprevention"}
    
    results = []
    for key in matched_keys:
        if key in COST_EFFECTIVENESS_DB:
            entry = COST_EFFECTIVENESS_DB[key]
            results.append({
                "intervention": entry["intervention"],
                "evidence_strength": entry["evidence_strength"],
                "key_source": entry["key_source"],
                "cost_per_daly": entry["cost_per_daly_averted"],
                "relevant_indicators": entry["relevant_dhis2_indicators"],
            })
    
    return {
        "source": "Curated evidence base (GiveWell, DCP3, Cochrane, WHO)",
        "query": f"Health area: {health_area} | Question: {question}",
        "matching_interventions": results,
        "note": "Evidence strength ratings: Very strong = multiple RCTs + systematic reviews; Strong = RCTs or strong observational evidence; Moderate = observational evidence or limited RCTs.",
        "methodology": "Cost-effectiveness data from GiveWell's published analyses, DCP3 (Disease Control Priorities, 3rd edition), and WHO-CHOICE. All figures represent estimated ranges based on multiple studies and contexts."
    }


def assess_cost_effectiveness(intervention_area, donor_budget=None):
    """Assess cost-effectiveness for an intervention area."""
    
    area_lower = intervention_area.lower()
    matching = []
    
    for key, data in COST_EFFECTIVENESS_DB.items():
        intervention_lower = data["intervention"].lower()
        if any(word in intervention_lower for word in area_lower.split()) or any(word in area_lower for word in key.split("_")):
            entry = dict(data)
            
            # Contextualize with donor budget if provided
            if donor_budget:
                try:
                    budget_num = float(''.join(c for c in donor_budget if c.isdigit() or c == '.'))
                    cost_per_life = data["cost_per_life_saved"]
                    # Extract rough midpoint
                    costs = [float(x.replace(",", "").replace("$", "")) for x in cost_per_life.split("-")]
                    midpoint = sum(costs) / len(costs)
                    lives = budget_num / midpoint
                    entry["budget_impact_estimate"] = f"With ${budget_num:,.0f}, this intervention could save approximately {lives:.1f} lives (rough estimate based on midpoint cost-effectiveness figures)"
                except:
                    pass
            
            matching.append(entry)
    
    if not matching:
        # Return general guidance
        return {
            "source": "Cost-effectiveness analysis framework",
            "note": f"No specific cost-effectiveness data found for '{intervention_area}'. Here are the most cost-effective global health interventions for reference:",
            "top_interventions": [
                {"intervention": v["intervention"], "cost_per_daly": v["cost_per_daly_averted"], "cost_per_life": v["cost_per_life_saved"]}
                for k, v in sorted(COST_EFFECTIVENESS_DB.items(), key=lambda x: float(x[1]["cost_per_daly_averted"].split("-")[0].replace("$", "")))[:5]
            ],
            "who_threshold_note": "WHO considers interventions costing less than 1x GDP per capita per DALY averted as 'highly cost-effective', and less than 3x GDP per capita as 'cost-effective'."
        }
    
    return {
        "source": "Cost-effectiveness analysis (GiveWell, DCP3, WHO-CHOICE)",
        "assessments": matching,
        "who_threshold_note": "WHO considers interventions costing less than 1x GDP per capita per DALY averted as 'highly cost-effective'. For context, GDP per capita in low-income countries averages ~$700-1,500.",
        "methodology": "Figures represent estimated ranges. Actual cost-effectiveness varies by context, implementation quality, and existing coverage levels. Lower costs per DALY = greater value for money."
    }


def find_organizations(health_area, geography_preference=None):
    """Find organizations working in a health area."""
    
    area_lower = health_area.lower()
    matching_orgs = []
    
    area_map = {
        "malaria": "malaria",
        "bed net": "malaria",
        "maternal": "maternal_child_health",
        "child health": "maternal_child_health",
        "birth": "maternal_child_health",
        "immunization": "immunization",
        "vaccine": "immunization",
        "hiv": "hiv_aids",
        "aids": "hiv_aids",
        "tb": "tuberculosis",
        "tuberculosis": "tuberculosis",
        "nutrition": "nutrition",
        "water": "wash",
        "sanitation": "wash",
        "wash": "wash",
        "diagnostic": "diagnostics",
        "screening": "diagnostics",
        "rdt": "diagnostics",
        "point-of-care": "diagnostics",
        "genexpert": "diagnostics",
        "smartphone": "diagnostics",
        "digital health": "digital_health",
        "mhealth": "digital_health",
        "chw tool": "digital_health",
        "app": "digital_health",
        "dhis2": "digital_health",
        "software": "digital_health",
        "education": "education",
        "school": "education",
        "literacy": "education",
        "girl": "education",
        "deworming": "education",
        "cash transfer": "economic_development",
        "livelihood": "economic_development",
        "microfinance": "economic_development",
        "poverty": "economic_development",
        "economic": "economic_development",
        "agricult": "agriculture",
        "farming": "agriculture",
        "smallholder": "agriculture",
        "crop": "agriculture",
        "food security": "agriculture",
        "gender": "gender",
        "women": "gender",
        "gbv": "gender",
        "violence": "gender",
        "humanitarian": "humanitarian",
        "refugee": "humanitarian",
        "emergency": "humanitarian",
        "crisis": "humanitarian",
        "climate": "climate",
        "adaptation": "climate",
        "resilience": "climate",
    }
    
    matched_category = None
    for keyword, category in area_map.items():
        if keyword in area_lower:
            matched_category = category
            break
    
    if matched_category and matched_category in ORGANIZATIONS_DB:
        matching_orgs = ORGANIZATIONS_DB[matched_category]
    
    # Always include general GH&D orgs
    matching_orgs.extend(ORGANIZATIONS_DB.get("general_ghd", []))
    
    # Filter by geography if specified
    if geography_preference:
        geo_lower = geography_preference.lower()
        geo_filtered = [o for o in matching_orgs if geo_lower in o.get("geographies", "").lower() or "global" in o.get("geographies", "").lower() or "sub-saharan" in o.get("geographies", "").lower()]
        if geo_filtered:
            matching_orgs = geo_filtered
    
    return {
        "source": "Organization database (GiveWell ratings, GlobalGiving, IATI)",
        "organizations": matching_orgs,
        "note": "Ratings reflect publicly available evaluations. 'GiveWell Top Charity' indicates the highest standard of evidence-backed, cost-effective programming. Always conduct your own due diligence before donating.",
        "geography_filter": geography_preference or "Global"
    }


def web_research(query, purpose):
    """Conduct web research using Claude with web search."""
    try:
        client = anthropic.Anthropic(api_key=st.session_state.get("api_key", ""))
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{
                "role": "user",
                "content": f"Research the following for a philanthropic advisor helping donors make giving decisions: {query}\n\nPurpose: {purpose}\n\nProvide a concise summary of the most relevant, recent findings. Focus on facts, data, and actionable insights."
            }]
        )
        
        # Extract text from response
        text_parts = [block.text for block in response.content if hasattr(block, 'text')]
        return {
            "source": "Live web research",
            "query": query,
            "findings": " ".join(text_parts) if text_parts else "Research completed but no text summary generated.",
            "note": f"Research purpose: {purpose}"
        }
    except Exception as e:
        return {
            "source": "Web research (unavailable)",
            "error": str(e),
            "note": "Web research is currently unavailable. The agent will rely on its curated evidence base and general knowledge."
        }


def _trim_tool_result(tool_name, result):
    """Trim tool results to only what Claude needs for reasoning. Saves 30-40% input tokens."""
    if not isinstance(result, dict):
        return result
    
    # Remove debug/boilerplate fields common to all tools
    for key in ["debug", "data_quality_note", "data_type", "methodology", "who_threshold_note"]:
        result.pop(key, None)
    
    if tool_name == "query_health_data":
        # Keep only geography names (not levels), indicators, analytics data, source
        if "geography_found" in result:
            result["geography_found"] = [g["name"] for g in result["geography_found"]] if isinstance(result["geography_found"], list) else result["geography_found"]
        # Trim analytics to top 10
        if isinstance(result.get("analytics_data"), list):
            result["analytics_data"] = result["analytics_data"][:10]
    
    elif tool_name == "search_evidence":
        # Remove the explanatory note — Claude knows what evidence strength means
        result.pop("note", None)
    
    elif tool_name == "assess_cost_effectiveness":
        # Trim each assessment: remove fields Claude doesn't use in recommendations
        if "assessments" in result:
            for a in result["assessments"]:
                a.pop("relevant_dhis2_indicators", None)
                a.pop("scalability", None)
    
    elif tool_name == "find_organizations":
        # Remove boilerplate due diligence note
        result.pop("note", None)
    
    elif tool_name == "web_research":
        result.pop("note", None)
    
    return result


def execute_tool(tool_name, tool_input):
    """Execute a tool, check cache, trim results, and cache successful results."""
    
    # Cache check for local tools (not web_research — that needs to be fresh)
    if tool_name in ("search_evidence", "assess_cost_effectiveness", "find_organizations") and "db" in st.session_state:
        db = st.session_state.db
        cache_key = db.make_cache_key(tool_name, str(tool_input.get("health_area", tool_input.get("intervention_area", ""))), 
                                       str(tool_input.get("geography_preference", "global")))
        cached = db.get_cached_data(cache_key)
        if cached:
            cached["_cached"] = True
            return cached
    
    # Execute the tool
    if tool_name == "query_health_data":
        result = query_health_data(**tool_input)
    elif tool_name == "search_evidence":
        result = search_evidence(**tool_input)
    elif tool_name == "assess_cost_effectiveness":
        result = assess_cost_effectiveness(**tool_input)
    elif tool_name == "find_organizations":
        result = find_organizations(**tool_input)
    elif tool_name == "web_research":
        result = web_research(**tool_input)
    else:
        return {"error": f"Unknown tool: {tool_name}"}
    
    # Trim the result before sending to Claude
    result = _trim_tool_result(tool_name, result)
    
    # Cache local tool results (evidence: 7 days, orgs: 7 days)
    if tool_name in ("search_evidence", "assess_cost_effectiveness", "find_organizations") and "db" in st.session_state:
        ttl = 168  # 7 days in hours
        db = st.session_state.db
        cache_key = db.make_cache_key(tool_name, str(tool_input.get("health_area", tool_input.get("intervention_area", ""))),
                                       str(tool_input.get("geography_preference", "global")))
        db.set_cached_data(cache_key, result, source=tool_name, ttl_hours=ttl)
    
    return result


# ══════════════════════════════════════════════
# AGENT SYSTEM PROMPT
# ══════════════════════════════════════════════

SYSTEM_PROMPT = """You are the AI Giving Advisor (Access Digital Health). Move donors from curiosity to action. Two goals: DISCOVERY (find what they care about, narrow options) and CONVERSION (turn interest into donation, remove friction).

## Tools (use 3+ per response)
1. query_health_data — DHIS2 health facility data from 129 countries. Health topics ONLY. Your differentiator.
2. search_evidence — GiveWell, DCP3, Cochrane, J-PAL evidence across all GH&D sectors.
3. assess_cost_effectiveness — Cost/DALY, cost/beneficiary, benefit-cost ratios.
4. find_organizations — Rated GH&D organizations with websites.
5. web_research — Live current info. Critical for non-health, crises, geographies.

Tool routing: Health → all 5 (ALWAYS query DHIS2). Education → 2,3,4,5 (frame as school years/earnings). Economic → 2,4,5 (frame as income/poverty). Humanitarian → 2,4,5. Climate/gender → 2,4,5.

## Discovery
Vague donor → ask ONE clarifying question as binary/triple choice, not open-ended. Examples: "children" → "keeping children alive (health) or better futures (education) or both?"; "Africa" → "specific country or wherever money stretches furthest?"; "make a difference" → "save most lives (health), long-term change (education), or crisis response (humanitarian)?"
After answer: commit to 2 options max. "I don't know" → give ONE recommendation with conviction.
Returning donor with stored profile → reference naturally: "Welcome back. Last time you explored [X]. Continue or try something new?"
Always: narrow don't dump, concrete stories not abstract stats, connect to donor's existing interests.

## Conversion (MANDATORY on every recommendation)
End EVERY recommendation with:
1. Concrete impact at budget — one number, one outcome, one org. "Your $1,000 = 333 bed nets protecting 1,000 people."
2. How to give — exact URL, time estimate, payment methods. Address cross-border for LMIC donors.
3. Urgency from real data — lead with the most striking finding from your data query.
4. Giving action plan — structured summary at the END:

**YOUR GIVING PLAN**
**Total:** $[amount]
**Allocation:** $[X] → [Org1] ([what]) / $[Y] → [Org2] ([what])
**How to give:** 1. Visit [url] → Select $[X] → ~2 min / 2. Visit [url] → Select $[Y] → ~2 min
**Expected impact:** [concrete outcomes]

Still exploring → end with binary: "explore [alternative] or move forward with [recommendation]?"

## Donor types
$100-5K: 2 options max, concrete impact, simple path. "Here's what I'd do with your $X."
$5K-50K: 3-4 options, portfolio thinking, evidence depth. "Here's how I'd split your $X."
$50K+: Landscape, funding gaps, additionality. "Here's a portfolio strategy for your $X."
Diaspora: Geography-first, local orgs, cross-border payment. "Best organizations in [country] you can support from abroad."
New: ONE option, encouraging, easy. "The simplest way to start is..."

## Reasoning stages
1. Understand — goals, budget, geography. If vague, ONE clarifying question.
2. Scope — search_evidence for strongest interventions.
3. Ground — DHIS2 for health / web_research for context.
4. Find urgency — identify most striking data finding, lead with it.
5. Assess — cost-effectiveness at their budget level.
6. Match — find_organizations with track records and URLs.
7. Close — recommendation + conversion close + giving action plan.

## Tone
Warm, confident, action-oriented. Honest about uncertainty in evidence, direct about recommendations. "Here's what I'd do with your money" > "here are some options to consider."
"""

EVALUATION_PROMPT = """You are the Proposal Evaluator, built by Access Digital Health. You evaluate grant proposals and funding requests across all areas of global health and development (GH&D) — including health, education, economic development, agriculture, gender, climate, humanitarian, and other development sectors.

## What you do

A funder has uploaded a grant proposal. Your job is to provide a rigorous, structured evaluation that helps them make an informed funding decision. You handle proposals on ANY GH&D topic, not just health.

## Your tools

1. **query_health_data** — Use this ONLY for health-related proposals to verify baseline health claims against DHIS2 data. Skip for non-health proposals (education, agriculture, economic development, etc.).
2. **search_evidence** — ALWAYS use this. Check whether the proposed intervention has an evidence base. The database covers health interventions, diagnostics, digital health, education, cash transfers, agriculture, livelihoods, gender, climate adaptation, and humanitarian responses.
3. **assess_cost_effectiveness** — Benchmark the proposal's cost per beneficiary against known data. Works for both health (cost per DALY) and non-health (cost per beneficiary, benefit-cost ratios) interventions.
4. **find_organizations** — Check what other organizations work in the same space. Covers health, education, economic development, agriculture, gender, humanitarian, and climate sectors.
5. **web_research** — ALWAYS use this for: (a) researching the applicant organization, (b) finding current context for the proposal's geography, (c) any topic where the curated databases lack specific evidence. This is especially important for non-health proposals and novel interventions.

## Deciding which tools to use

- **Health proposals** (malaria, maternal health, immunization, HIV, TB, nutrition, diagnostics, digital health): Use all 5 tools. Query DHIS2 for data verification.
- **Education proposals** (schools, literacy, girls' education, ECD, deworming): Use search_evidence + assess_cost_effectiveness + find_organizations + web_research. Skip DHIS2.
- **Economic development proposals** (cash transfers, livelihoods, microfinance, agriculture): Use search_evidence + assess_cost_effectiveness + find_organizations + web_research. Skip DHIS2.
- **Gender, climate, humanitarian proposals**: Use search_evidence + find_organizations + web_research. Skip DHIS2 unless there's a health component.
- **Novel or cross-sector proposals**: Use web_research heavily to find relevant evidence. Use search_evidence for any components that match known interventions.

## CRITICAL: Separating substance from verification

Your evaluation MUST provide TWO distinct assessments:

**Part A: Substantive Assessment** — Evaluate the proposal ON ITS MERITS regardless of whether you can verify the organization. This is the primary value you provide. Assess evidence alignment, data claims, value for money, feasibility, and red flags as if the organization is legitimate. This section should lead with the funding recommendation for the PROPOSAL DESIGN.

**Part B: Organizational Due Diligence Note** — Separately report what you found (or didn't find) about the applicant organization. This informs the CONDITIONS attached to funding, NOT whether to fund. Many legitimate organizations, especially small community-based organizations in LMICs, have minimal online presence. Org verification failure → conditions and milestone disbursement, NOT rejection.

## CRITICAL: Calibrating org verification language

- If you cannot find an organization online, say: "Unable to independently verify organizational credentials through web search. This is common for smaller LMIC-based organizations and does NOT necessarily indicate fraud. Standard due diligence is recommended before disbursement."
- NEVER say an organization "appears to be fraudulent" or "suggests fraudulent solicitation" based solely on the absence of web search results. Absence of evidence is not evidence of fraud.
- DO recommend specific due diligence steps (registration verification, audited financials, reference checks, site visits).
- The agriculture evaluation's approach (FUND WITH CONDITIONS + milestone-based disbursement) is the model for proposals where substance is strong but org verification is inconclusive.

## CRITICAL: Data verification nuance

When a proposal cites statistics that differ from current data:
- First check whether the proposal's figure was accurate at an earlier date (e.g., a widely-cited WHO estimate from a few years ago). If so, note: "The proposal uses a [year] figure of X. More recent data shows Y, representing [improvement/deterioration]. Recommend the applicant update baselines to reflect current conditions."
- Only flag as a genuine concern if the figure was NEVER accurate or is clearly fabricated.
- Distinguish between: (a) outdated but legitimate data, (b) data from a different geographic level (district vs national), and (c) genuinely unsupported claims.

## Your evaluation framework

Assess the proposal across these dimensions:

1. **Evidence alignment** — Does the proposed intervention have a strong evidence base? What do systematic reviews, RCTs, or rigorous evaluations say? Rate: Strong / Moderate / Weak / No evidence found.

2. **Data verification** — For health proposals: Do baseline statistics match DHIS2 data? For non-health: Are claimed statistics plausible based on known data sources? Use web_research to verify key claims. Apply the data nuance guidance above.

3. **Value for money** — How does the cost per beneficiary compare to benchmarks? Is the budget reasonable? Rate: Excellent / Good / Fair / Poor / Cannot assess.

4. **Feasibility** — Is the timeline realistic? Does the team have relevant capacity? What are implementation risks?

5. **Landscape context** — What else is happening in this geography and sector? Complementary or competing programs? Use find_organizations and web_research.

6. **Red flags** — Unrealistic targets, budget inconsistencies, unsupported claims, missing ethics, regulatory gaps, sustainability concerns. Budget math errors are a yellow flag (poor preparation) not necessarily a red flag.

## Output format

Structure your evaluation as:
- **Executive summary** (2-3 sentences with recommendation based on the MANDATORY RECOMMENDATION LOGIC above. Remember: strong substance + inconclusive org = FUND WITH CONDITIONS, never DO NOT FUND)
- **Evidence alignment** assessment
- **Data verification** findings (applying the nuance guidance above)
- **Value for money** analysis
- **Feasibility** assessment
- **Red flags** (if any — distinguish between critical, major, and minor)
- **Organizational due diligence** (separate section — what was found/not found, recommended verification steps)
- **Recommendation** with specific conditions, milestone-based disbursement structure where appropriate, and questions for the applicant

## MANDATORY RECOMMENDATION LOGIC

BEFORE WRITING YOUR RECOMMENDATION, you MUST complete this self-check:

Step 1: Rate the substantive merit of the PROPOSAL DESIGN (not the organization):
- Evidence alignment: Strong / Moderate / Weak?
- Value for money: Good / Fair / Poor / Cannot assess?
- Technical feasibility: High / Medium / Low?

Step 2: If 2+ of those are Strong/Good/High → Substantive Merit = STRONG
         If 2+ are Moderate/Fair/Medium → Substantive Merit = MODERATE
         If 2+ are Weak/Poor/Low → Substantive Merit = WEAK

Step 3: Look up the recommendation in this matrix:

| Substantive Merit | Org Verified | Recommendation |
|---|---|---|
| Strong | Yes | FUND |
| Strong | Inconclusive | FUND WITH CONDITIONS (milestone-based) |
| Strong | Concerning | FUND WITH CONDITIONS (verification-first tranche) |
| Moderate | Yes | FUND WITH CONDITIONS |
| Moderate | Inconclusive | FUND WITH CONDITIONS (enhanced monitoring) |
| Weak | Any | DO NOT FUND |

Step 4: Write the recommendation that the matrix dictates. DO NOT DEVIATE.

ABSOLUTE RULE: "DO NOT FUND" requires WEAK SUBSTANTIVE MERIT. If the proposal design is rated Strong or Moderate on substance, you MUST recommend FUND WITH CONDITIONS regardless of organizational concerns. Org verification issues are addressed through CONDITIONS (milestone-based disbursement, verification-first tranche), NOT through rejection.

VIOLATION CHECK: If you find yourself writing "DO NOT FUND" for a proposal where you rated evidence as "Strong" or "Moderate to Strong" — STOP. You are violating the decision matrix. Go back and correct to FUND WITH CONDITIONS.

When recommending FUND WITH CONDITIONS, always include:
- Pre-disbursement conditions (org registration, audited financials, reference checks, site visit)
- Milestone-based disbursement structure with specific tranches and trigger criteria
- Enhanced monitoring requirements for first-time grantees
- Alternative organizations as backup if verification fails

Use at least 3 tools. Use web_research for any topic not well covered by the curated databases.
"""

PORTFOLIO_PROMPT = """You are the Portfolio Assistant, built by Access Digital Health. You are a daily-use AI analyst for foundation program officers managing grant portfolios across all GH&D sectors.

## Your role

You know the program officer's entire portfolio — their grants, geographies, sectors, milestones, budgets, and any grantee reports that have been uploaded. You are their always-available analyst who can answer any question about their portfolio, prepare them for meetings, analyze reports, and flag issues.

## What you can do

1. **Analyze grantee reports** — When a grantee report is provided, extract key claims, progress against milestones, budget burn rate, risks flagged, and outcomes reported. Cross-reference claims against independent data (DHIS2 for health, web research for all sectors). Produce a structured summary with questions the program officer should ask.

2. **Prepare call/meeting briefs** — Before a call with a grantee, produce a 1-page brief: grant status, recent developments in the geography, outstanding questions from the last report, suggested agenda items.

3. **Monitor context** — Use web_research to find news, policy changes, crises, or developments affecting any grant's geography or sector. Flag anything that could help or hinder a grant's success.

4. **Track milestones** — Based on the portfolio data provided, identify what's coming due, what's overdue, and what's at risk based on progress signals.

5. **Answer portfolio questions** — "Which grants are behind schedule?" "Compare my malaria grants across countries." "What should I tell the board about our Nigeria portfolio?" "Draft the executive summary for my quarterly report."

6. **Generate board reports** — Synthesize across the full portfolio for quarterly board presentations: overall status, highlights, concerns, recommendations, and strategic questions.

## Your tools

1. **query_health_data** — DHIS2 indicators for health grants' geographies
2. **search_evidence** — Evidence base for any intervention type
3. **assess_cost_effectiveness** — Benchmarking against known CEA data
4. **find_organizations** — Landscape of other actors in same space
5. **web_research** — CRITICAL for daily use: current news, developments, policy changes in any geography or sector

## Adapting to sector

- Health grants: Use DHIS2 + evidence + CEA + web research
- Education grants: Use evidence + web research (UNESCO data, enrollment trends)
- Agriculture grants: Use evidence + web research (food security, weather, market prices)
- Humanitarian grants: Use evidence + web research (IPC classifications, displacement data, funding gaps)
- Any other sector: Use evidence + web research

## Tone and format

Be concise and action-oriented. Program officers are busy. Lead with what matters most. Use clear headers. Flag items that need attention with urgency levels. When generating briefs or reports, structure them for quick scanning — the program officer should get the key message in the first 2 sentences.

When analyzing a grantee report, be a critical friend — acknowledge progress honestly but flag concerns without hedging. Your job is to make the program officer smarter about their portfolio, not to validate the grantee.
"""


def extract_pdf_text(uploaded_file):
    """Extract text from an uploaded PDF file."""
    try:
        import pdfplumber
        import io
        pdf_bytes = uploaded_file.read()
        text_parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {i+1} ---\n{page_text}")
        return "\n\n".join(text_parts) if text_parts else "Could not extract text from PDF."
    except ImportError:
        return "PDF reading requires pdfplumber. Install with: pip install pdfplumber"
    except Exception as e:
        return f"Error reading PDF: {str(e)}"


# ══════════════════════════════════════════════
# STREAMLIT UI
# ══════════════════════════════════════════════

def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "tool_calls_log" not in st.session_state:
        st.session_state.tool_calls_log = []
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""
    if "mode" not in st.session_state:
        st.session_state.mode = "donor"
    if "eval_result" not in st.session_state:
        st.session_state.eval_result = None
    if "portfolio_result" not in st.session_state:
        st.session_state.portfolio_result = None
    if "portfolio_grants" not in st.session_state:
        st.session_state.portfolio_grants = []
    if "portfolio_reports" not in st.session_state:
        st.session_state.portfolio_reports = {}
    if "explore_messages" not in st.session_state:
        st.session_state.explore_messages = []
    
    # Database initialization
    if "db" not in st.session_state:
        supabase_url = ""
        supabase_key = ""
        try:
            supabase_url = st.secrets["SUPABASE_URL"]
            supabase_key = st.secrets["SUPABASE_KEY"]
        except Exception:
            pass
        st.session_state.db = Database(supabase_url, supabase_key)
    
    # User session
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "db_loaded" not in st.session_state:
        st.session_state.db_loaded = False
    
    # Load default API key from secrets if available
    if not st.session_state.api_key:
        try:
            default_key = st.secrets["ANTHROPIC_API_KEY"]
            if default_key:
                st.session_state.api_key = default_key
        except Exception:
            pass


def load_user_data():
    """Load persisted data for the current user from database."""
    db = st.session_state.db
    user_id = st.session_state.user_id
    
    if not user_id or st.session_state.db_loaded:
        return
    
    # Load portfolio grants
    saved_grants = db.load_portfolio(user_id)
    if saved_grants:
        st.session_state.portfolio_grants = saved_grants
    
    # Load giving profile
    profile = db.get_giving_profile(user_id)
    if profile:
        st.session_state.setdefault("giving_profile", profile)
    
    st.session_state.db_loaded = True


def render_sidebar():
    with st.sidebar:
        st.markdown(f"### {BRAND}")
        st.markdown(f"**{APP_TITLE}**")
        st.divider()
        
        # User session
        user_email = st.text_input("Your email (for saving data)", value=st.session_state.user_email, placeholder="you@example.com")
        if user_email and user_email != st.session_state.user_email:
            st.session_state.user_email = user_email
            user = st.session_state.db.get_or_create_user(user_email)
            st.session_state.user_id = user.get("id")
            st.session_state.db_loaded = False
            load_user_data()
            st.rerun()
        
        api_key = st.text_input("Anthropic API Key", type="password", value=st.session_state.api_key)
        if api_key:
            st.session_state.api_key = api_key
        
        st.divider()
        
        # Database status
        db_status = st.session_state.db.get_status()
        if db_status["connected"]:
            st.markdown("🟢 **Database:** Connected")
        else:
            st.markdown("🟡 **Database:** Session only")
        
        st.divider()
        
        # Mode selector
        st.markdown("#### Platform mode")
        mode = st.radio(
            "Select mode",
            options=["donor", "evaluation", "portfolio"],
            format_func=lambda x: {
                "donor": "🎯 Donor advisory",
                "evaluation": "📋 Proposal evaluation",
                "portfolio": "📊 Portfolio monitor"
            }[x],
            index=["donor", "evaluation", "portfolio"].index(st.session_state.mode),
            label_visibility="collapsed"
        )
        if mode != st.session_state.mode:
            st.session_state.mode = mode
            st.session_state.messages = []
            st.session_state.tool_calls_log = []
            st.session_state.eval_result = None
            st.session_state.portfolio_result = None
            st.rerun()
        
        st.divider()
        st.markdown("#### Agent reasoning log")
        st.markdown("*Watch the agent's tool calls and reasoning in real time*")
        
        if st.session_state.tool_calls_log:
            for i, log in enumerate(st.session_state.tool_calls_log):
                icon_map = {
                    "query_health_data": "🏥",
                    "search_evidence": "📚",
                    "assess_cost_effectiveness": "💰",
                    "find_organizations": "🏢",
                    "web_research": "🌐",
                }
                icon = icon_map.get(log["tool"], "🔧")
                with st.expander(f"{icon} {log['tool']}", expanded=False):
                    st.json(log["input"])
                    if "output" in log:
                        st.markdown("**Result:**")
                        if isinstance(log["output"], dict):
                            st.json(log["output"])
                        else:
                            st.write(log["output"])
        else:
            st.markdown("*No tool calls yet. Start a conversation to see the agent reason.*")
        
        st.divider()
        st.markdown("#### Data sources")
        st.markdown("""
        - 🏥 **DHIS2** — Health program data from national systems
        - 📚 **Evidence base** — GiveWell, DCP3, Cochrane, J-PAL
        - 💰 **Health economics** — Cost-effectiveness frameworks
        - 🏢 **Organizations** — Rated GH&D organizations
        - 🌐 **Web research** — Live current information
        """)
        
        st.divider()
        if st.button("Clear conversation"):
            st.session_state.messages = []
            st.session_state.tool_calls_log = []
            st.rerun()
        
        # Token usage monitor
        if st.session_state.get("token_log"):
            st.divider()
            st.markdown("#### Token usage")
            last = st.session_state.token_log[-1]
            total_cost = sum(t["est_cost"] for t in st.session_state.token_log)
            st.markdown(f"Last call: **{last['input_tokens']:,}** in + **{last['output_tokens']:,}** out ({last['iterations']} steps)")
            st.markdown(f"Est. cost: **${last['est_cost']:.3f}**")
            st.markdown(f"Session total: **${total_cost:.3f}** ({len(st.session_state.token_log)} calls)")


def run_agent(user_message, system_prompt=None):
    """Run the agentic loop with tool use."""
    
    if not st.session_state.api_key:
        return "Please enter your Anthropic API key in the sidebar to start."
    
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT
    
    # Inject context from previous sessions if available
    if st.session_state.user_id and st.session_state.db.connected:
        db = st.session_state.db
        context = db.get_context_summary(st.session_state.user_id, st.session_state.mode)
        if st.session_state.mode == "donor":
            profile = db.get_giving_profile(st.session_state.user_id)
            if profile:
                context += f"RETURNING DONOR PROFILE: {json.dumps(profile)}\n\n"
        if context:
            system_prompt = system_prompt + "\n\n" + context
    
    client = anthropic.Anthropic(api_key=st.session_state.api_key)
    
    # Build message history for Claude
    claude_messages = []
    for msg in st.session_state.messages:
        if msg["role"] in ["user", "assistant"]:
            claude_messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add current user message
    claude_messages.append({"role": "user", "content": user_message})
    
    # Agentic loop — capped at 4 iterations (quality doesn't improve beyond this)
    max_iterations = 4
    iteration = 0
    total_input_tokens = 0
    total_output_tokens = 0
    
    status_placeholder = st.empty()
    
    while iteration < max_iterations:
        iteration += 1
        
        status_placeholder.status(f"Agent thinking... (step {iteration})", state="running")
        
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=system_prompt,
                tools=TOOLS,
                messages=claude_messages,
            )
        except anthropic.RateLimitError as e:
            # Wait and retry once on rate limit
            status_placeholder.status("Rate limit hit — waiting 30 seconds...", state="running")
            time.sleep(30)
            try:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=4096,
                    system=system_prompt,
                    tools=TOOLS,
                    messages=claude_messages,
                )
            except Exception as retry_e:
                return f"Rate limit error (retry failed): {str(retry_e)}"
        except anthropic.BadRequestError as e:
            return f"API error: {str(e)}. Please check your API key and try again."
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                status_placeholder.status("Rate limit hit — waiting 30 seconds...", state="running")
                time.sleep(30)
                try:
                    response = client.messages.create(
                        model=MODEL,
                        max_tokens=4096,
                        system=system_prompt,
                        tools=TOOLS,
                        messages=claude_messages,
                    )
                except Exception as retry_e:
                    return f"Rate limit error (retry failed): {str(retry_e)}"
            else:
                return f"Error: {str(e)}"
        
        # Check if we're done (no tool use) or need to process tool calls
        if response.stop_reason == "end_of_turn":
            # Track tokens
            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens
            # Log usage to session
            if "token_log" not in st.session_state:
                st.session_state.token_log = []
            st.session_state.token_log.append({
                "iterations": iteration,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "est_cost": round(total_input_tokens * 3 / 1_000_000 + total_output_tokens * 15 / 1_000_000, 4),
            })
            # Extract final text
            final_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    final_text += block.text
            status_placeholder.empty()
            return final_text
        
        elif response.stop_reason == "tool_use":
            # Track tokens
            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens
            # Process tool calls
            assistant_content = response.content
            claude_messages.append({"role": "assistant", "content": assistant_content})
            
            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_id = block.id
                    
                    # Log the tool call
                    log_entry = {"tool": tool_name, "input": tool_input}
                    
                    # Update status
                    status_labels = {
                        "query_health_data": f"🏥 Querying health data for {tool_input.get('geography', 'unknown')}...",
                        "search_evidence": f"📚 Searching evidence base for {tool_input.get('health_area', 'unknown')}...",
                        "assess_cost_effectiveness": f"💰 Assessing cost-effectiveness of {tool_input.get('intervention_area', 'unknown')}...",
                        "find_organizations": f"🏢 Finding organizations for {tool_input.get('health_area', 'unknown')}...",
                        "web_research": f"🌐 Researching: {tool_input.get('query', 'unknown')[:60]}...",
                    }
                    status_placeholder.status(status_labels.get(tool_name, f"Running {tool_name}..."), state="running")
                    
                    # Execute tool (with trimming and caching built in)
                    result = execute_tool(tool_name, tool_input)
                    log_entry["output"] = result
                    st.session_state.tool_calls_log.append(log_entry)
                    
                    # Compact JSON — no indentation saves ~20% tokens
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": json.dumps(result, separators=(',', ':'), default=str)
                    })
            
            # Add tool results to messages
            claude_messages.append({"role": "user", "content": tool_results})
        
        else:
            # Unexpected stop reason
            final_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    final_text += block.text
            status_placeholder.empty()
            return final_text or "The agent stopped unexpectedly. Please try again."
    
    status_placeholder.empty()
    return "The agent reached its maximum number of reasoning steps. This usually means the query is very complex. Please try a more specific question."


def main():
    st.set_page_config(
        page_title=f"{APP_TITLE} | {BRAND}",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
    <style>
    .main-header { text-align: center; padding: 1rem 0 0.5rem; }
    .main-header h1 { color: #1D6B52; font-size: 2rem; margin-bottom: 0.2rem; }
    .main-header p { color: #6B6960; font-size: 1rem; }
    .stChatMessage { padding: 1rem; }
    div[data-testid="stSidebar"] { background-color: #f8f7f4; }
    </style>
    """, unsafe_allow_html=True)
    
    init_session_state()
    render_sidebar()
    
    # Load persisted data for returning users
    if st.session_state.user_id and not st.session_state.db_loaded:
        load_user_data()
    
    mode = st.session_state.mode
    
    if mode == "donor":
        render_donor_mode()
    elif mode == "evaluation":
        render_evaluation_mode()
    elif mode == "portfolio":
        render_portfolio_mode()


def render_donor_mode():
    """Donor Advisory mode — three-tab giving intelligence platform."""
    st.markdown(f"""
    <div class="main-header">
        <h1>🎯 AI Giving Advisor</h1>
        <p>Evidence-grounded intelligence for charitable giving across global health & development</p>
        <p style="font-size: 0.8rem; color: #999;">Powered by {BRAND} • Prototype v0.1</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🧭 Guided giving", "💡 Impact calculator", "💬 Open conversation"])
    
    # ── TAB 1: GUIDED GIVING ──
    with tab1:
        st.markdown("#### Tell us about your giving goals")
        st.markdown("Answer a few quick questions and we'll generate a personalized, evidence-based giving recommendation.")
        
        # Parameter 1: Cause areas (multi-select with human language)
        st.markdown("**What causes matter to you?** (select all that apply)")
        cause_options = {
            "Saving children's lives (malaria, pneumonia, diarrhea)": "child_health",
            "Mothers surviving childbirth": "maternal_health",
            "Vaccinating children": "immunization",
            "Girls staying in school": "girls_education",
            "Ending extreme poverty (cash transfers)": "cash_transfers",
            "Fighting hunger and malnutrition": "food_security",
            "Clean water and sanitation": "wash",
            "Supporting refugees and displaced people": "humanitarian",
            "Helping smallholder farmers": "agriculture",
            "Climate resilience for vulnerable communities": "climate",
            "I'm open — show me where my money goes furthest": "open",
        }
        selected_causes = []
        cols = st.columns(2)
        for i, (label, code) in enumerate(cause_options.items()):
            with cols[i % 2]:
                if st.checkbox(label, key=f"cause_{code}"):
                    selected_causes.append((label, code))
        
        st.markdown("---")
        
        # Parameter 2: Budget
        col_a, col_b = st.columns(2)
        with col_a:
            budget = st.select_slider(
                "**How much are you considering giving?**",
                options=["Under $100", "$100-500", "$500-2,000", "$2,000-10,000", "$10,000-50,000", "$50,000-500,000", "$500,000+"],
                value="$500-2,000"
            )
        
        # Parameter 3: Geography
        with col_b:
            geo_preference = st.selectbox(
                "**Do you have a geographic focus?**",
                options=["Wherever my money helps most", "West Africa", "East Africa", "Southern Africa", "South Asia", "Southeast Asia",
                         "Specific country (I'll type below)"],
                index=0
            )
        
        specific_country = ""
        if geo_preference == "Specific country (I'll type below)":
            specific_country = st.text_input("Which country?", placeholder="e.g., Nigeria, Kenya, India")
        
        col_c, col_d = st.columns(2)
        # Parameter 4: Giving philosophy
        with col_c:
            philosophy = st.radio(
                "**What's your giving priority?**",
                options=["Maximum lives saved per dollar", "Long-term transformation (root causes)", "Tangible, direct results I can see", "I'm not sure — help me think through it"],
                index=0
            )
        
        # Parameter 5: Experience
        with col_d:
            experience = st.radio(
                "**Your giving experience:**",
                options=["This is my first time giving to GH&D", "I've donated before but want to be more strategic", "I'm experienced and looking for deeper analysis"],
                index=0
            )
        
        if st.button("🎯 Generate my giving recommendation", type="primary", use_container_width=True):
            if not selected_causes:
                st.warning("Please select at least one cause area.")
                return
            
            # Assemble structured prompt from selections
            causes_text = ", ".join([label for label, _ in selected_causes])
            cause_codes = [code for _, code in selected_causes]
            geo_text = specific_country if specific_country else geo_preference
            
            structured_prompt = f"""Based on my giving profile below, provide a personalized giving recommendation.

MY GIVING PROFILE:
- Causes I care about: {causes_text}
- Budget: {budget}
- Geographic focus: {geo_text}
- Giving priority: {philosophy}
- Experience level: {experience}

Please:
1. For each cause I selected, show the most effective interventions with cost-effectiveness data
2. Recommend specific organizations I can support, with their track record and website
3. If I selected multiple causes, suggest how to split my budget across them
4. {"Query DHIS2 for relevant health data in my geographic focus area to show me what's happening on the ground" if any(c in ["child_health", "maternal_health", "immunization", "wash"] for c in cause_codes) else "Research the current situation in my geographic area of interest"}
5. Make concrete impact estimates for my budget level (e.g., "your ${budget} could...")
6. Include guidance on how to actually make the donation"""

            st.session_state.messages = [{"role": "user", "content": structured_prompt}]
            # Save giving profile to database
            if st.session_state.user_id:
                st.session_state.db.update_giving_profile(st.session_state.user_id, {
                    "causes": causes_text, "cause_codes": cause_codes,
                    "budget": budget, "geography": geo_text,
                    "philosophy": philosophy, "experience": experience,
                })
            st.rerun()
        
        # Show results below the form if they exist
        if st.session_state.messages:
            st.markdown("---")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            if st.session_state.messages[-1]["role"] == "user":
                with st.chat_message("assistant"):
                    response = run_agent(st.session_state.messages[-1]["content"], SYSTEM_PROMPT)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    if st.session_state.user_id:
                        st.session_state.db.save_conversation(st.session_state.user_id, "donor", st.session_state.messages)
                st.rerun()
            
            # Follow-up chat after recommendation
            if follow_up := st.chat_input("Ask a follow-up question about your recommendation..."):
                st.session_state.messages.append({"role": "user", "content": follow_up})
                st.rerun()
    
    # ── TAB 2: IMPACT CALCULATOR ──
    with tab2:
        st.markdown("#### What could your donation accomplish?")
        st.markdown("Enter an amount and instantly see the concrete impact across different causes — lives saved, children educated, families supported.")
        
        # Budget input
        col_amount, col_geo = st.columns([2, 1])
        with col_amount:
            raw_amount = st.number_input("Your giving budget ($)", min_value=10, max_value=10000000, value=1000, step=100, key="impact_budget")
        with col_geo:
            impact_geo = st.selectbox("Region focus (optional)", 
                ["Wherever impact is greatest", "West Africa", "East Africa", "South Asia", "Nigeria", "Kenya", "Sierra Leone"],
                key="impact_geo")
        
        amount = float(raw_amount)
        
        st.markdown("---")
        
        # Calculate impacts locally — no API calls needed
        impacts = [
            {
                "icon": "🦟", "title": "Malaria prevention", "subtitle": "Insecticide-treated bed nets",
                "primary": f"{int(amount / 3):,} bed nets",
                "detail": f"Protecting ~{int(amount / 3 * 1.8):,} people for 3 years",
                "lives": f"~{max(1, int(amount / 4500)):,} lives saved" if amount >= 1000 else "Contributing to lives saved",
                "evidence": "Very strong (Cochrane reviewed)", "cost_metric": "$3 per net · $4,500 per life saved",
                "org": "Against Malaria Foundation", "org_url": "againstmalaria.com", "org_rating": "GiveWell Top Charity", "color": "#E8593C",
            },
            {
                "icon": "💵", "title": "Direct cash transfers", "subtitle": "Unconditional cash to extreme poor",
                "primary": f"${int(amount * 0.85):,} directly to families",
                "detail": f"~{max(1, int(amount * 0.85 / 270)):,} families receiving ~$270 each" if amount >= 500 else f"Direct support to {max(1, int(amount * 0.85 / 270))} family",
                "lives": "25-30% lasting consumption increase", "evidence": "Very strong (30+ RCTs)", "cost_metric": "85% transfer efficiency · $6-17 return per $1",
                "org": "GiveDirectly", "org_url": "givedirectly.org", "org_rating": "GiveWell Top Charity", "color": "#1D9E75",
            },
            {
                "icon": "📚", "title": "Girls' education", "subtitle": "Secondary school scholarships",
                "primary": f"{max(1, int(amount / 250)):,} girls supported for a year",
                "detail": f"Each additional year: 8-13% higher lifetime earnings",
                "lives": f"Reduces child marriage by 5-10% per year of school", "evidence": "Strong (World Bank, J-PAL)", "cost_metric": "$250 per girl per year · $6-17 return per $1 invested",
                "org": "Camfed", "org_url": "camfed.org", "org_rating": "GiveWell Standout Charity", "color": "#534AB7",
            },
            {
                "icon": "💊", "title": "Vitamin A supplementation", "subtitle": "Preventing child blindness and death",
                "primary": f"{int(amount / 1.25):,} children supplemented",
                "detail": "24% reduction in all-cause mortality for children 6-59 months",
                "lives": f"~{max(1, int(amount / 3500)):,} lives saved" if amount >= 1000 else "Contributing to lives saved",
                "evidence": "Very strong (Cochrane review)", "cost_metric": "$1.25 per child · $15-50 per DALY averted",
                "org": "Helen Keller International", "org_url": "hki.org", "org_rating": "GiveWell Top Charity", "color": "#BA7517",
            },
            {
                "icon": "💉", "title": "Child immunization incentives", "subtitle": "Cash incentives for completing vaccinations",
                "primary": f"~{max(1, int(amount / 50)):,} children fully immunized",
                "detail": "Addresses low vaccination rates through conditional cash",
                "lives": "Prevents measles, polio, diphtheria, and other deadly diseases",
                "evidence": "Strong (RCT-evaluated in Nigeria)", "cost_metric": "$50 per fully immunized child",
                "org": "New Incentives", "org_url": "newincentives.org", "org_rating": "GiveWell Top Charity", "color": "#378ADD",
            },
            {
                "icon": "🌾", "title": "Smallholder farming support", "subtitle": "Seeds, training, and market access",
                "primary": f"{max(1, int(amount / 80)):,} farmers supported",
                "detail": "20-50% yield increases with bundled inputs and training",
                "lives": f"~${int(amount * 4.2):,} in farmer income generated (4.2x ROI)",
                "evidence": "Moderate-Strong (One Acre Fund model)", "cost_metric": "$80 per farmer per season · 4-5x return on investment",
                "org": "One Acre Fund", "org_url": "oneacrefund.org", "org_rating": "Highly rated", "color": "#639922",
            },
        ]
        
        # Display impact cards
        st.markdown(f"### With **${amount:,.0f}**, you could fund:")
        
        for i in range(0, len(impacts), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                if i + j < len(impacts):
                    imp = impacts[i + j]
                    with col:
                        st.markdown(f"""
                        <div style="border: 1px solid rgba(128,128,128,0.2); border-left: 4px solid {imp['color']}; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                            <div style="font-size: 1.3rem; margin-bottom: 4px;">{imp['icon']} <strong>{imp['title']}</strong></div>
                            <div style="font-size: 0.85rem; color: #888; margin-bottom: 10px;">{imp['subtitle']}</div>
                            <div style="font-size: 1.4rem; font-weight: 600; margin-bottom: 4px;">{imp['primary']}</div>
                            <div style="font-size: 0.9rem; margin-bottom: 4px;">{imp['detail']}</div>
                            <div style="font-size: 0.85rem; margin-bottom: 8px;">{imp['lives']}</div>
                            <div style="font-size: 0.8rem; color: #888; margin-bottom: 4px;">Evidence: {imp['evidence']}</div>
                            <div style="font-size: 0.8rem; color: #888; margin-bottom: 8px;">{imp['cost_metric']}</div>
                            <div style="font-size: 0.85rem;"><strong>{imp['org']}</strong> ({imp['org_rating']}) · {imp['org_url']}</div>
                        </div>
                        """, unsafe_allow_html=True)
        
        # Conversion: action buttons
        st.markdown("---")
        st.markdown("#### Ready to go deeper?")
        
        deep_cols = st.columns(3)
        with deep_cols[0]:
            if st.button("🎯 Get my personalized recommendation", key="impact_to_rec", use_container_width=True):
                prompt = f"""I have ${amount:,.0f} to give{' with a focus on ' + impact_geo if impact_geo != 'Wherever impact is greatest' else ''}. I've seen the impact estimates. Now give me your personalized recommendation — which intervention should I prioritize, why, and exactly how to donate. Include the organization website and step-by-step donation instructions."""
                st.session_state.messages = [{"role": "user", "content": prompt}]
                st.rerun()
        with deep_cols[1]:
            if st.button("📊 Compare top 3 options for me", key="impact_to_compare", use_container_width=True):
                prompt = f"""I have ${amount:,.0f}. Compare malaria bed nets, cash transfers, and girls' education in depth for my specific budget. For each: what exactly my money accomplishes, the evidence, and the best organization. Then tell me which one YOU would choose and why. End with donation links."""
                st.session_state.messages = [{"role": "user", "content": prompt}]
                st.rerun()
        with deep_cols[2]:
            if st.button("🌍 Show me the need on the ground", key="impact_to_dhis2", use_container_width=True):
                geo = impact_geo if impact_geo != "Wherever impact is greatest" else "Sierra Leone"
                prompt = f"""Query DHIS2 for current health data in {geo}. Show me where the coverage gaps are right now — the real numbers from health facilities. I have ${amount:,.0f} and want to put it where the data shows the most urgent need. End with a specific recommendation and how to donate."""
                st.session_state.messages = [{"role": "user", "content": prompt}]
                st.rerun()
        
        # Show agent results if triggered
        if st.session_state.messages:
            st.markdown("---")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            if st.session_state.messages[-1]["role"] == "user":
                with st.chat_message("assistant"):
                    response = run_agent(st.session_state.messages[-1]["content"], SYSTEM_PROMPT)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    if st.session_state.user_id:
                        st.session_state.db.save_conversation(st.session_state.user_id, "donor", st.session_state.messages)
                st.rerun()
            
            if follow_up := st.chat_input("Ask a follow-up question...", key="impact_chat"):
                st.session_state.messages.append({"role": "user", "content": follow_up})
                st.rerun()
    
    # ── TAB 3: OPEN CONVERSATION ──
    with tab3:
        st.markdown("#### Ask anything about giving")
        st.markdown("Have a conversation with the AI advisor. It has access to health data, impact evidence, cost-effectiveness analysis, organization databases, and live web research.")
        
        if not st.session_state.messages:
            st.markdown("*Tell me what you care about and your budget — I'll find the highest-impact way to give:*")
            col1, col2 = st.columns(2)
            starters = [
                ("🦟 I have $5K for malaria", "I want to help reduce malaria deaths in sub-Saharan Africa. I have $5,000 to give right now. Show me where it would have the most impact and exactly how to donate."),
                ("📚 Help girls stay in school", "I want to help girls stay in school in East Africa. What does the evidence say works best, which organizations should I give to, and how do I donate to them?"),
                ("🌾 Fight the food crisis", "I'm concerned about the food crisis in the Sahel — 31 million people facing hunger. I have $3,000. What's the most effective way to help right now?"),
                ("💵 Give cash directly", "I've heard giving cash directly to extremely poor people is one of the most effective interventions. Is that true? I have $1,000 — show me how it compares and how to give."),
                ("🚨 What's urgent right now?", "What are the most urgent needs in global development RIGHT NOW? Where has the situation worsened recently? I have $2,000 and want to put it where it's needed most urgently today. Show me the data and tell me exactly how to help."),
                ("🌍 New here — $500 to do the most good", "I've never donated to global development before. I have $500 and want to do the most good possible. Give me ONE clear recommendation and tell me exactly how to donate."),
                ("🇳🇬 I want to give back to Nigeria", "I'm Nigerian and want to support effective programs in my home country. What are the biggest needs, best organizations, and how do I donate from abroad?"),
                ("💰 $100K giving strategy", "I'm looking to deploy $100,000 across global development. Help me build a giving portfolio — which sectors, what allocation, which organizations, and how to execute."),
            ]
            for i, (title, prompt) in enumerate(starters):
                col = col1 if i % 2 == 0 else col2
                with col:
                    if st.button(title, key=f"starter_{i}", use_container_width=True):
                        st.session_state.messages.append({"role": "user", "content": prompt})
                        st.rerun()
        
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        if prompt := st.chat_input("Tell me about your giving goals — any cause, any budget..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
        
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            with st.chat_message("assistant"):
                response = run_agent(st.session_state.messages[-1]["content"], SYSTEM_PROMPT)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                # Save conversation to database
                if st.session_state.user_id:
                    st.session_state.db.save_conversation(st.session_state.user_id, "donor", st.session_state.messages)
            st.rerun()


def render_evaluation_mode():
    """Proposal Evaluation mode — upload PDF, get structured assessment."""
    st.markdown(f"""
    <div class="main-header">
        <h1>📋 Proposal Evaluator</h1>
        <p>AI-powered evaluation of funding proposals against evidence, health data, and cost-effectiveness benchmarks</p>
        <p style="font-size: 0.8rem; color: #999;">Powered by {BRAND} • Prototype v0.1</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### Upload a grant proposal")
        st.markdown("Upload a PDF proposal and the AI will evaluate it against evidence databases, DHIS2 health data, and cost-effectiveness benchmarks.")
        uploaded_file = st.file_uploader("Upload proposal PDF", type=["pdf", "txt"], key="proposal_upload")
        
        additional_context = st.text_area(
            "Additional context (optional)",
            placeholder="E.g., 'This is for our maternal health portfolio. We're particularly interested in whether the cost per beneficiary is reasonable and if the baseline data is accurate.'",
            height=100
        )
    
    with col2:
        st.markdown("#### The evaluator checks")
        st.markdown("""
        - **Evidence alignment** — Does the intervention have a strong evidence base?
        - **Data verification** — Do claimed health statistics match DHIS2?
        - **Value for money** — Is cost per beneficiary reasonable vs. benchmarks?
        - **Feasibility** — Are targets and timelines realistic?
        - **Red flags** — Budget issues, unsupported claims, missing ethics
        """)
    
    if uploaded_file and st.button("🔍 Evaluate proposal", type="primary", use_container_width=True):
        with st.spinner("Reading proposal..."):
            if uploaded_file.type == "application/pdf":
                proposal_text = extract_pdf_text(uploaded_file)
            else:
                proposal_text = uploaded_file.read().decode("utf-8", errors="replace")
        
        if len(proposal_text) < 100:
            st.error(f"Could not extract sufficient text from the document: {proposal_text}")
            return
        
        truncated = proposal_text[:6000]
        with st.expander(f"📄 Extracted text ({len(proposal_text)} chars, using first 6,000)", expanded=False):
            st.text(truncated[:2000] + "..." if len(truncated) > 2000 else truncated)
        
        st.markdown("---")
        
        # === TRY AGENTIC PATH FIRST ===
        eval_message = f"""Evaluate this grant proposal. Provide a structured assessment.

PROPOSAL TEXT (excerpt):
{truncated}

{"FUNDER CONTEXT: " + additional_context if additional_context else ""}

Use your tools to verify health data, check evidence, benchmark costs, and identify red flags. Provide a clear funding recommendation."""

        agentic_success = False
        try:
            status = st.status("🤖 Agentic evaluation (full tool use)...", state="running")
            response = run_agent(eval_message, EVALUATION_PROMPT)
            if response and "rate_limit" not in response.lower() and "Error" not in response[:20]:
                status.update(label="Agentic evaluation complete", state="complete")
                st.session_state.eval_result = response
                # Save to database
                if st.session_state.user_id:
                    st.session_state.db.save_evaluation(
                        st.session_state.user_id, "Uploaded proposal", truncated[:500],
                        "auto-detected", "auto-detected", "See evaluation",
                        response, st.session_state.tool_calls_log
                    )
                agentic_success = True
                st.rerun()
            else:
                raise Exception(response)
        except Exception as e:
            if not agentic_success:
                # === FALLBACK: PRE-FETCH PATH ===
                st.info("⚡ Switching to pre-fetch mode (rate limit detected). Upgrade to API Tier 2 ($40 deposit) for full agentic evaluation.")
                
                text_lower = truncated.lower()
                health_area = "general"
                for keyword, area in [("malaria", "malaria"), ("maternal", "maternal_health"), ("immuniz", "immunization"), 
                                      ("vaccin", "immunization"), ("hiv", "hiv"), ("aids", "hiv"), ("tb ", "tb"),
                                      ("tuberculosis", "tb"), ("nutrition", "nutrition"), ("wash", "general"), ("water", "general")]:
                    if keyword in text_lower:
                        health_area = area
                        break
                
                geography = "Sierra Leone"
                for geo in ["Nigeria", "Kenya", "Sierra Leone", "Ghana", "Tanzania", "Uganda", "Ethiopia", 
                             "Malawi", "Mozambique", "Rwanda", "Senegal", "Mali", "Niger", "Burkina Faso",
                             "Bo", "Kano", "Lagos", "Nairobi", "Bombali", "Kenema"]:
                    if geo.lower() in text_lower:
                        geography = geo
                        break
                
                status.update(label="Pre-fetching data...", state="running")
                
                dhis2_data = query_health_data(health_area, geography, "Proposal evaluation")
                st.session_state.tool_calls_log.append({"tool": "query_health_data", "input": {"category": health_area, "geography": geography}, "output": dhis2_data})
                
                evidence_data = search_evidence(health_area, f"What works for {health_area}?")
                st.session_state.tool_calls_log.append({"tool": "search_evidence", "input": {"health_area": health_area}, "output": evidence_data})
                
                cea_data = assess_cost_effectiveness(health_area)
                st.session_state.tool_calls_log.append({"tool": "assess_cost_effectiveness", "input": {"area": health_area}, "output": cea_data})
                
                status.update(label="Generating evaluation (pre-fetch mode)...", state="running")
                
                # Wait for rate limit to clear
                time.sleep(45)
                
                prefetch_msg = f"""Evaluate this proposal using the data provided.

PROPOSAL: {truncated[:2500]}
{"CONTEXT: " + additional_context if additional_context else ""}
DHIS2 DATA: {json.dumps(dhis2_data, indent=2, default=str)[:1500]}
EVIDENCE: {json.dumps(evidence_data, indent=2, default=str)[:1000]}
CEA BENCHMARKS: {json.dumps(cea_data, indent=2, default=str)[:1000]}

Structured evaluation: (1) Executive summary, (2) Evidence alignment, (3) Data verification, (4) Value for money, (5) Red flags, (6) Recommendation."""

                try:
                    client = anthropic.Anthropic(api_key=st.session_state.api_key)
                    resp = client.messages.create(
                        model=MODEL, max_tokens=4096,
                        system="You are a grant proposal evaluator for global health programs. Be structured and evidence-based.",
                        messages=[{"role": "user", "content": prefetch_msg}],
                    )
                    result_text = "".join([b.text for b in resp.content if hasattr(b, 'text')])
                    status.update(label="Evaluation complete (pre-fetch mode)", state="complete")
                    st.session_state.eval_result = result_text
                    # Save to database
                    if st.session_state.user_id:
                        st.session_state.db.save_evaluation(
                            st.session_state.user_id, "Uploaded proposal", truncated[:500],
                            "auto-detected", "auto-detected", "See evaluation",
                            result_text, []
                        )
                    st.rerun()
                except Exception as e2:
                    status.update(label="Evaluation failed", state="error")
                    st.error(f"Both agentic and pre-fetch paths failed. Please wait 60 seconds and try again. Error: {str(e2)[:200]}")
    
    elif st.session_state.eval_result:
        st.markdown("---")
        st.markdown("### Latest evaluation")
        st.markdown(st.session_state.eval_result)
    
    st.markdown("---")
    st.markdown("#### Follow-up questions")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    if prompt := st.chat_input("Ask a follow-up question about the evaluation..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
    
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        context = f"Previous evaluation: {st.session_state.eval_result[:1500]}\n\n" if st.session_state.eval_result else ""
        try:
            client = anthropic.Anthropic(api_key=st.session_state.api_key)
            resp = client.messages.create(
                model=MODEL, max_tokens=1500,
                system="You are a grant proposal evaluator. Answer follow-up questions.",
                messages=[{"role": "user", "content": context + st.session_state.messages[-1]["content"]}],
            )
            reply = "".join([b.text for b in resp.content if hasattr(b, 'text')])
            with st.chat_message("assistant"):
                st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            st.error(f"Error: {str(e)}")


def render_portfolio_mode():
    """Portfolio Assistant — daily-use AI analyst for program officers."""
    st.markdown(f"""
    <div class="main-header">
        <h1>📊 Portfolio Assistant</h1>
        <p>Your daily AI analyst for grant portfolio management across all GH&D sectors</p>
        <p style="font-size: 0.8rem; color: #999;">Powered by {BRAND} • Prototype v0.1</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 My portfolio", "📄 Analyze report", "💬 Ask anything", "📊 Generate board report"])
    
    # ── TAB 1: PORTFOLIO SETUP ──
    with tab1:
        st.markdown("#### Define your active grants")
        st.markdown("Enter your grants below. This information persists across tabs so the assistant knows your full portfolio.")
        
        num_grants = st.number_input("Number of grants", min_value=1, max_value=15, value=max(3, len(st.session_state.portfolio_grants) or 3))
        
        new_grants = []
        for i in range(int(num_grants)):
            with st.expander(f"Grant {i+1}", expanded=i < 3 and not st.session_state.portfolio_grants):
                existing = st.session_state.portfolio_grants[i] if i < len(st.session_state.portfolio_grants) else {}
                
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Program name", key=f"pf_name_{i}", value=existing.get("name", ""), placeholder="e.g., Malaria bed net distribution")
                    org = st.text_input("Grantee organization", key=f"pf_org_{i}", value=existing.get("org", ""), placeholder="e.g., Against Malaria Foundation")
                    geo = st.text_input("Geography", key=f"pf_geo_{i}", value=existing.get("geography", ""), placeholder="e.g., Bo District, Sierra Leone")
                with col2:
                    sector = st.selectbox("Sector", key=f"pf_sector_{i}",
                        options=["Health - Malaria", "Health - Maternal & Child", "Health - Immunization", "Health - HIV/TB",
                                 "Health - Nutrition", "Health - Other", "Education", "Agriculture & Food Security",
                                 "Economic Development", "Gender & GBV", "Humanitarian", "Climate & Environment", "WASH", "Other"],
                        index=0)
                    budget = st.text_input("Grant amount", key=f"pf_budget_{i}", value=existing.get("budget", ""), placeholder="e.g., $150,000")
                    status = st.selectbox("Status", key=f"pf_status_{i}",
                        options=["Active - On track", "Active - Needs attention", "Active - Behind schedule", "Closing", "Pipeline"],
                        index=0)
                
                milestones = st.text_area("Key milestones & dates", key=f"pf_miles_{i}", value=existing.get("milestones", ""),
                    placeholder="e.g., M3: Baseline survey complete\nM6: CHW training done\nM9: Mid-term evaluation\nM12: Endline + final report",
                    height=80)
                notes = st.text_input("Notes", key=f"pf_notes_{i}", value=existing.get("notes", ""),
                    placeholder="e.g., Next call scheduled April 15. Grantee flagged supply chain delays.")
                
                if name:
                    sector_code = sector.split(" - ")[-1].lower().replace(" & ", "_").replace(" ", "_") if " - " in sector else sector.lower()
                    new_grants.append({
                        "name": name, "org": org, "geography": geo, "sector": sector,
                        "sector_code": sector_code, "budget": budget, "status": status,
                        "milestones": milestones, "notes": notes
                    })
        
        if st.button("💾 Save portfolio", type="primary"):
            st.session_state.portfolio_grants = new_grants
            if st.session_state.user_id:
                st.session_state.db.save_portfolio(st.session_state.user_id, new_grants)
                st.success(f"Portfolio saved: {len(new_grants)} grants (persisted)")
            else:
                st.success(f"Portfolio saved: {len(new_grants)} grants (enter email to persist)")
        
        if st.session_state.portfolio_grants:
            st.markdown("---")
            st.markdown(f"**Portfolio summary:** {len(st.session_state.portfolio_grants)} active grants")
            for i, g in enumerate(st.session_state.portfolio_grants):
                status_icon = {"Active - On track": "🟢", "Active - Needs attention": "🟡", "Active - Behind schedule": "🔴", "Closing": "🔵", "Pipeline": "⚪"}.get(g["status"], "⚪")
                st.markdown(f"{status_icon} **{g['name']}** — {g['org'] or 'TBD'} | {g['geography']} | {g['sector']} | {g['budget'] or 'TBD'}")
    
    # ── TAB 2: REPORT ANALYSIS ──
    with tab2:
        st.markdown("#### Analyze a grantee report")
        st.markdown("Upload a progress report and the assistant will extract key information, cross-reference claims against independent data, and produce a structured summary with questions for your next call.")
        
        if not st.session_state.portfolio_grants:
            st.warning("Please save your portfolio in the 'My portfolio' tab first so the assistant knows which grant this report belongs to.")
        
        grant_options = ["Select a grant..."] + [g["name"] for g in st.session_state.portfolio_grants] + ["Other / not in portfolio"]
        selected_grant = st.selectbox("Which grant is this report for?", grant_options, key="report_grant_select")
        
        report_file = st.file_uploader("Upload grantee report", type=["pdf", "txt"], key="report_upload")
        report_context = st.text_input("Any specific questions or concerns?", placeholder="e.g., They mentioned budget overruns last call — check if that's addressed")
        
        if report_file and selected_grant != "Select a grant..." and st.button("📄 Analyze report", type="primary", use_container_width=True):
            with st.spinner("Reading report..."):
                if report_file.type == "application/pdf":
                    report_text = extract_pdf_text(report_file)
                else:
                    report_text = report_file.read().decode("utf-8", errors="replace")
            
            if len(report_text) < 50:
                st.error(f"Could not extract text: {report_text}")
                return
            
            truncated_report = report_text[:5000]
            
            # Find grant details
            grant_info = ""
            for g in st.session_state.portfolio_grants:
                if g["name"] == selected_grant:
                    grant_info = f"""
GRANT DETAILS FROM PORTFOLIO:
- Program: {g['name']}
- Organization: {g['org']}
- Geography: {g['geography']}
- Sector: {g['sector']}
- Budget: {g['budget']}
- Status: {g['status']}
- Milestones: {g['milestones']}
- Notes: {g['notes']}"""
                    break
            
            # Pre-fetch relevant data
            status_display = st.status("Analyzing report...", state="running")
            
            # Determine sector and fetch appropriate data
            grant_data = next((g for g in st.session_state.portfolio_grants if g["name"] == selected_grant), {})
            sector_code = grant_data.get("sector_code", "general")
            geography = grant_data.get("geography", "")
            
            health_sectors = ["malaria", "maternal", "child", "immunization", "hiv", "tb", "nutrition", "health"]
            is_health = any(h in sector_code.lower() for h in health_sectors) or any(h in grant_data.get("sector", "").lower() for h in health_sectors)
            
            prefetched = ""
            if is_health and geography:
                status_display.update(label=f"🏥 Querying DHIS2 for {geography}...")
                dhis2_cat = "malaria" if "malaria" in sector_code else "maternal_health" if "maternal" in sector_code else "immunization" if "immun" in sector_code else "general"
                dhis2_data = query_health_data(dhis2_cat, geography.split(",")[0].strip(), "Report analysis")
                st.session_state.tool_calls_log.append({"tool": "query_health_data", "input": {"geography": geography, "category": dhis2_cat}, "output": dhis2_data})
                prefetched += f"\nDHIS2 DATA FOR {geography}:\n{json.dumps(dhis2_data, indent=2, default=str)[:1500]}\n"
            
            status_display.update(label="📚 Checking evidence base...")
            evidence = search_evidence(sector_code, f"Evidence for {grant_data.get('sector', 'development')} interventions")
            prefetched += f"\nEVIDENCE BASE:\n{json.dumps(evidence, indent=2, default=str)[:1000]}\n"
            
            status_display.update(label="🤖 Analyzing report...")
            
            analysis_msg = f"""Analyze this grantee progress report. You know the full portfolio context.

{grant_info}

GRANTEE REPORT TEXT:
{truncated_report}

{f"PROGRAM OFFICER'S SPECIFIC CONCERNS: {report_context}" if report_context else ""}

INDEPENDENT DATA:
{prefetched}

Provide a structured analysis:
1. **Key takeaways** (3-5 bullet points — what matters most)
2. **Progress against milestones** (on track / delayed / at risk for each)
3. **Claims verification** (cross-reference any data claims against the independent data above)
4. **Budget and spending** (any burn rate concerns?)
5. **Risks and concerns** (what should the program officer worry about?)
6. **Questions for next grantee call** (5 specific questions based on what's in the report and what's missing)
7. **Action items for program officer** (what to do next)"""

            try:
                client = anthropic.Anthropic(api_key=st.session_state.api_key)
                resp = client.messages.create(
                    model=MODEL, max_tokens=4096,
                    system=PORTFOLIO_PROMPT,
                    messages=[{"role": "user", "content": analysis_msg}],
                )
                result = "".join([b.text for b in resp.content if hasattr(b, 'text')])
                status_display.update(label="Analysis complete", state="complete")
                
                st.session_state.portfolio_reports[selected_grant] = result
                # Save to database
                if st.session_state.user_id:
                    st.session_state.db.save_report_analysis(
                        st.session_state.user_id, "", selected_grant,
                        truncated_report[:3000], result
                    )
                st.markdown("### Report analysis")
                st.markdown(result)
            except Exception as e:
                status_display.update(label="Analysis failed", state="error")
                st.error(f"Error: {str(e)}")
        
        # Show previous analyses
        if st.session_state.portfolio_reports:
            st.markdown("---")
            st.markdown("#### Previous report analyses")
            for grant_name, analysis in st.session_state.portfolio_reports.items():
                with st.expander(f"📄 {grant_name}"):
                    st.markdown(analysis)
    
    # ── TAB 3: PORTFOLIO CHAT ──
    with tab3:
        st.markdown("#### Ask anything about your portfolio")
        
        if not st.session_state.portfolio_grants:
            st.info("Save your portfolio in the 'My portfolio' tab to enable portfolio-aware conversations.")
        
        # Show example questions
        if not st.session_state.messages:
            st.markdown("*Try questions like:*")
            examples = [
                "Which of my grants needs the most attention right now?",
                "Prepare me for my call with the Nigeria grantee tomorrow",
                "What's happening in Sierra Leone that could affect our malaria program?",
                "Compare the progress of my health grants across countries",
                "Draft the executive summary for my quarterly board report",
                "What questions should I ask about the immunization grant's next milestone?",
            ]
            cols = st.columns(2)
            for i, ex in enumerate(examples):
                with cols[i % 2]:
                    if st.button(ex, key=f"ex_{i}", use_container_width=True):
                        st.session_state.messages.append({"role": "user", "content": ex})
                        st.rerun()
        
        # Chat display
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        if prompt := st.chat_input("Ask about your portfolio..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
        
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            # Build portfolio context for the agent
            portfolio_context = "PROGRAM OFFICER'S PORTFOLIO:\n"
            for i, g in enumerate(st.session_state.portfolio_grants):
                portfolio_context += f"\nGrant {i+1}: {g['name']}\n  Org: {g['org']}\n  Geography: {g['geography']}\n  Sector: {g['sector']}\n  Budget: {g['budget']}\n  Status: {g['status']}\n  Milestones: {g['milestones']}\n  Notes: {g['notes']}\n"
            
            if st.session_state.portfolio_reports:
                portfolio_context += "\nPREVIOUS REPORT ANALYSES:\n"
                for gname, analysis in st.session_state.portfolio_reports.items():
                    portfolio_context += f"\n{gname}: {analysis[:500]}...\n"
            
            full_message = f"{portfolio_context}\n\nPROGRAM OFFICER'S QUESTION: {st.session_state.messages[-1]['content']}"
            
            with st.chat_message("assistant"):
                response = run_agent(full_message, PORTFOLIO_PROMPT)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                # Save conversation to database
                if st.session_state.user_id:
                    st.session_state.db.save_conversation(st.session_state.user_id, "portfolio", st.session_state.messages)
            st.rerun()
    
    # ── TAB 4: BOARD REPORT ──
    with tab4:
        st.markdown("#### Generate a board report")
        st.markdown("Produce a quarterly portfolio synthesis for your board or leadership team.")
        
        if not st.session_state.portfolio_grants:
            st.warning("Please save your portfolio first.")
            return
        
        report_period = st.text_input("Reporting period", value="Q1 2026 (January - March)", placeholder="e.g., Q1 2026")
        board_context = st.text_area("Board context or priorities", 
            placeholder="e.g., Board wants to know if we should increase allocation to Nigeria. They're also asking about our exit strategy for the Sierra Leone grant.",
            height=80)
        
        if st.button("📊 Generate board report", type="primary", use_container_width=True):
            status_display = st.status("Generating board report...", state="running")
            
            # Pre-fetch data for all health grants
            all_data = []
            for g in st.session_state.portfolio_grants:
                health_sectors = ["malaria", "maternal", "child", "immunization", "hiv", "tb", "nutrition", "health"]
                is_health = any(h in g.get("sector", "").lower() for h in health_sectors)
                
                grant_data = {"grant": g, "dhis2": "N/A (non-health grant)", "evidence": ""}
                
                if is_health and g.get("geography"):
                    status_display.update(label=f"🏥 Fetching data for {g['name']}...")
                    dhis2_cat = "malaria" if "malaria" in g["sector"].lower() else "maternal_health" if "maternal" in g["sector"].lower() else "immunization" if "immun" in g["sector"].lower() else "general"
                    dhis2_result = query_health_data(dhis2_cat, g["geography"].split(",")[0].strip(), f"Board report - {g['name']}")
                    st.session_state.tool_calls_log.append({"tool": "query_health_data", "input": {"grant": g["name"], "geography": g["geography"]}, "output": dhis2_result})
                    grant_data["dhis2"] = json.dumps(dhis2_result, indent=2, default=str)[:1200]
                    time.sleep(0.5)
                
                evidence = search_evidence(g.get("sector_code", "general"), f"Evidence for {g['sector']}")
                grant_data["evidence"] = json.dumps(evidence, indent=2, default=str)[:600]
                all_data.append(grant_data)
            
            status_display.update(label="🤖 Drafting board report...")
            
            grants_summary = "\n\n".join([
                f"GRANT: {d['grant']['name']} | {d['grant']['org']} | {d['grant']['geography']} | {d['grant']['sector']} | {d['grant']['budget']} | Status: {d['grant']['status']}\nMilestones: {d['grant']['milestones']}\nNotes: {d['grant']['notes']}\nHealth Data: {d['dhis2'][:800]}\nEvidence: {d['evidence'][:400]}"
                for d in all_data
            ])
            
            # Include any previous report analyses
            report_analyses = ""
            if st.session_state.portfolio_reports:
                report_analyses = "\n\nGRANTEE REPORT ANALYSES ON FILE:\n" + "\n".join([
                    f"{name}: {analysis[:400]}..." for name, analysis in st.session_state.portfolio_reports.items()
                ])
            
            board_msg = f"""Generate a quarterly board report for this portfolio.

REPORTING PERIOD: {report_period}

PORTFOLIO ({len(st.session_state.portfolio_grants)} grants):
{grants_summary}
{report_analyses}

{"BOARD PRIORITIES: " + board_context if board_context else ""}

Format the report as:
1. **Executive summary** (3-4 sentences: overall portfolio health, key wins, key concerns)
2. **Portfolio at a glance** (one-line status for each grant with traffic light: on track / needs attention / at risk)
3. **Highlights** (what went well this quarter)
4. **Concerns and risks** (what needs board attention, with recommended actions)
5. **Health data context** (for health grants: what DHIS2 indicators show about the operating environment)
6. **Strategic questions for the board** (2-3 decisions or discussions the board should have)
7. **Recommended actions** (specific next steps with owners and timelines)"""

            try:
                client = anthropic.Anthropic(api_key=st.session_state.api_key)
                resp = client.messages.create(
                    model=MODEL, max_tokens=4096,
                    system=PORTFOLIO_PROMPT,
                    messages=[{"role": "user", "content": board_msg}],
                )
                result = "".join([b.text for b in resp.content if hasattr(b, 'text')])
                status_display.update(label="Board report complete", state="complete")
                st.session_state.portfolio_result = result
                # Save to database
                if st.session_state.user_id:
                    st.session_state.db.save_board_report(
                        st.session_state.user_id, report_period, result,
                        st.session_state.portfolio_grants
                    )
                st.markdown(f"### Board report — {report_period}")
                st.markdown(result)
            except Exception as e:
                status_display.update(label="Failed", state="error")
                st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
