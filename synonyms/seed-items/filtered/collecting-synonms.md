Collect a few synonms for each kept CUI from UMLS

```sql
SELECT STR, SAB, TTY
FROM MRCONSO
WHERE CUI=:<CUI_STRING_GOES_HERE!> AND LAT='ENG' AND SUPPRESS='N'
  AND SAB IN ('SNOMEDCT_US','MSH','RXNORM','LNC','ICD9CM')
  AND TTY IN ('PT','SY','FN','BN','IN')
LIMIT 50;
```

To:do

clean them:

- lowercase, trim, dedupe

- drop qualifiers that add severity/site/time (e.g., “acute”, “left/right”, “>96 hours”)

- keep 3–10 short, useful forms (include common abbr like “hgb”, “mi” if present)
