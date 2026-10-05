# Procurement and grading references

PYAazScan is a **decision-support prototype for external visual inspection**, not a certifying authority. A buyer's signed, current procurement specification must determine the actual grade.

## Default demo rules

The bundled, editable `DEMO_45_65` profile uses a 45–65 mm diameter interval as an **engineering demonstration assumption** (also matching the illustrative interval in the project brief). It treats visible rot and sprouting as reject conditions, minor visible damage as URS, and low-confidence or uncalibrated decisions as manual review. These are not represented as current NAFED, NCCF, AGMARK, or statutory rules. Inspectors can edit the profile in **Rules & policy** and every inspection/report snapshots its rule ID and version.

The Small Farmers’ Agribusiness Consortium (SFAC) produce-quality reference describes 4.0–6.5 cm as a preferred onion diameter range and discusses visible selection/rejection characteristics. It is a useful context source, not proof of a universally binding procurement standard. See [sources.json](sources.json).

The 2006 AGMARK export procedure and USDA grade standards are included as historical or comparative reading only. Their scope and jurisdiction differ from a current Indian procurement contract. Do not copy a size/defect tolerance into a contract without confirming the applicable document and date.

## Rule governance

1. Obtain the buyer's current written specification and jurisdiction.
2. Record the issuing body, document title, version/date, commodity/variety, and any lot tolerances.
3. Have an authorised procurement officer approve the rule profile.
4. Validate measurement accuracy, defect definitions, sampling protocol, and tolerances before operational deployment.
5. Keep a versioned rule snapshot with each inspection; a later rule edit must not rewrite earlier decisions.

## Scope limitations

This prototype assesses only what is visible in a single RGB photograph. It cannot certify internal rot, firmness, maturity, moisture, weight, smell, pesticide residues, or lot-wide prevalence from an unrepresentative sample. Defect tolerances are not inferred from pixel counts. Manual examination and the approved procurement process remain authoritative.
