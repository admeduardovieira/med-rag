Database: umls.db

==================================================
Found 4 table(s):

---

Table: MRDEF
Rows: 466842
Columns (8):

- CUI: varchar
- AUI: varchar
- ATUI: varchar
- SATUI: varchar
- SAB: varchar
- DEF: TEXT
- SUPPRESS: varchar
- CVF: varchar

**Sample rows (up to 3):**

Row 1: {'CUI': 'C0000039', 'AUI': 'A0016515', 'ATUI': 'AT38152019', 'SATUI': '', 'SAB': 'MSH', 'DEF': 'Synthetic phospholipid used in liposomes and lipid bilayers to study biological membranes. It is also a major constituent of PULMONARY SURFACTANTS.', 'SUPPRESS': 'N', 'CVF': ''}
Row 2: {'CUI': 'C0000039', 'AUI': 'A11754881', 'ATUI': 'AT69817678', 'SATUI': '', 'SAB': 'MSHSWE', 'DEF': 'Syntetisk fosfolipid som används i liposomer och lipidlager för att studera biologiska membran. Den är också en huvudbeståndsdel i lungytaktiva substanser.', 'SUPPRESS': 'N', 'CVF': ''}
Row 3: {'CUI': 'C0000039', 'AUI': 'A13042554', 'ATUI': 'AT264439104', 'SATUI': '', 'SAB': 'MSHCZE', 'DEF': 'Syntetický fosfolipid používaný v liposomech a lipidových dvojvrstvách ke studiu biologických membrán. Je také hlavní součástí PLICNÍCH SURFAKTANTŮ.', 'SUPPRESS': 'N', 'CVF': ''}

---

Table: MRCONSO
Rows: 17144356
Columns (18):

- CUI: varchar
- LAT: varchar
- TS: varchar
- LUI: varchar
- STT: varchar
- SUI: varchar
- ISPREF: varchar
- AUI: varchar
- SAUI: varchar
- SCUI: varchar
- SDUI: varchar
- SAB: varchar
- TTY: varchar
- CODE: varchar
- STR: TEXT
- SRL: varchar
- SUPPRESS: varchar
- CVF: varchar

**Sample rows (up to 3):**

Row 1: {'CUI': 'C0000005', 'LAT': 'ENG', 'TS': 'P', 'LUI': 'L0000005', 'STT': 'PF', 'SUI': 'S0007492', 'ISPREF': 'Y', 'AUI': 'A26634265', 'SAUI': '', 'SCUI': 'M0019694', 'SDUI': 'D012711', 'SAB': 'MSH', 'TTY': 'PEP', 'CODE': 'D012711', 'STR': '(131)I-Macroaggregated Albumin', 'SRL': '0', 'SUPPRESS': 'N', 'CVF': '256'}

Row 2: {'CUI': 'C0000005', 'LAT': 'ENG', 'TS': 'P', 'LUI': 'L0000005', 'STT': 'PF', 'SUI': 'S0007492', 'ISPREF': 'Y', 'AUI': 'A26634265', 'SAUI': '', 'SCUI': 'M0019694', 'SDUI': 'D012711', 'SAB': 'MSH', 'TTY': 'PEP', 'CODE': 'D012711', 'STR': '(131)I-Macroaggregated Albumin', 'SRL': '0', 'SUPPRESS': 'N', 'CVF': '256'}

Row 3: {'CUI': 'C0000005', 'LAT': 'FRE', 'TS': 'P', 'LUI': 'L6220710', 'STT': 'PF', 'SUI': 'S7133957', 'ISPREF': 'Y', 'AUI': 'A13433185', 'SAUI': '', 'SCUI': 'M0019694', 'SDUI': 'D012711', 'SAB': 'MSHFRE', 'TTY': 'PEP', 'CODE': 'D012711', 'STR': "Macroagrégats d'albumine marquée à l'iode 131", 'SRL': '3', 'SUPPRESS': 'N', 'CVF': ''}

---

Table: MRSTY
Rows: 3798191
Columns (6):

- CUI: varchar
- TUI: varchar
- STN: varchar
- STY: TEXT
- ATUI: varchar
- CVF: varchar

**Sample rows (up to 3):**

Row 1: {'CUI': 'C0000005', 'TUI': 'T116', 'STN': 'A1.4.1.2.1.7', 'STY': 'Amino Acid, Peptide, or Protein', 'ATUI': 'AT17648347', 'CVF': '256'}
Row 2: {'CUI': 'C0000005', 'TUI': 'T121', 'STN': 'A1.4.1.1.1', 'STY': 'Pharmacologic Substance', 'ATUI': 'AT17575038', 'CVF': '256'}
Row 3: {'CUI': 'C0000005', 'TUI': 'T130', 'STN': 'A1.4.1.1.4', 'STY': 'Indicator, Reagent, or Diagnostic Aid', 'ATUI': 'AT17634323', 'CVF': '256'}

---

Table: descriptions
Rows: 4090623
Columns (6):

- CUI: TEXT
- LAT: TEXT
- SAB: TEXT
- TTY: TEXT
- STR: TEXT
- STY: TEXT

**Sample rows (up to 3):**

Row 1: {'CUI': 'C0000005', 'LAT': 'ENG', 'SAB': 'MSH', 'TTY': 'PEP', 'STR': '(131)I-Macroaggregated Albumin', 'STY': 'T116|T121|T130'}
Row 2: {'CUI': 'C0000039', 'LAT': 'ENG', 'SAB': 'MTH', 'TTY': 'PN', 'STR': '1,2-dipalmitoylphosphatidylcholine', 'STY': 'T109|T121'}
Row 3: {'CUI': 'C0000039', 'LAT': 'ENG', 'SAB': 'MSH', 'TTY': 'MH', 'STR': '1,2-Dipalmitoylphosphatidylcholine', 'STY': 'T109|T121'}

---
