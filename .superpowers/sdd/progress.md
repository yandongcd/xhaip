# SDD Progress â€” åˆ›ä¼¤éª¨ç§‘è¯Šç–—é—¨æˆ·

Plan: docs/superpowers/plans/2026-07-13-ortho-portal.md
Branch: master (file-level commits; pre-existing WIP in tree)

- Task 1: æ‰©å…… his_adapter æ‚£è€…åˆ° 5 ä½ â€” complete (commit cf1c86e, review clean; reviewer's Important finding on missing `)` was a false positive from diff encoding â€” verified P002/P004 correct)
  - Minor deferred: unused `client` in test (needed by Tasks 2-5); query_imaging docstring edit is pre-existing WIP
- Task 2: æ–°å¢ /ortho-portal è·¯ç”± + HTML éª¨æ¶ â€” complete (commit e5907d8, review clean; note: tests use HAIP_TEST_MODE for auth bypass)
- Task 3: é—¨æˆ· HTML å¸ƒå±€ + è®¾è®¡ä»¤ç‰Œ â€” complete (commit a180d58, review clean, 10/10 tests)
  - Minor deferred: no trailing newline in html; `.p-card.active` bg hardcoded rgba(10,132,255,.12) (light-mode tint mismatch) â€” consider color-mix in Task 5/final
- Task 4: é—¨æˆ· JS æ‚£è€…é˜Ÿåˆ—/èƒ½åŠ›å¡/é˜¶æ®µæ¸²æŸ“ â€” complete (commit 5b5ff8d, review clean, 13/13 tests; emoji/wording "drift" findings were diff-encoding false positives)
  - Minor deferred: no trailing newline in html (recurring)
- Task 5: é—¨æˆ· KPI èšåˆ + èƒ½åŠ›å¡æ‰§è¡Œ â€” complete (commit b3d617e, review clean, 19/19 tests)
  - Minor deferred: `V1_ENDPOINTS` const in production JS is a test-only artifact (paths built via concat elsewhere) â€” consider refining test to assert concat pattern instead
- Task 6: å›å½’ + Lint + æ‰‹åŠ¨éªŒæ”¶ â€” complete (automated parts)
  - ortho-portal 19/19 + test_orthopedic.py pass; ruff clean; E2E TestClient(HAIP_TEST_MODE=true) OK
  - PRE-EXISTING out of scope: 6 TestDemoPage failures (demo html vs YAML roster) â€” not touched by this feature
  - auth bypass requires HAIP_TEST_MODE="true"

## Final whole-branch review (30e140e..b3d617e) â€” Ready to merge WITH FIXES
Fix batch dispatched (I1,I2,M2,M3):
- I1: V1_ENDPOINTS dead code â†’ wire into runtime or remove + fix test
- I2: computeKpi undercounts denominator on partial failure â†’ count n independently
- M2: add trailing newline
- M3: badge() maps electiveâ†’"high" red (should be neutral)
Noted, NOT fixing (match existing codebase patterns): I3 innerHTML (36+ uses repo-wide), I4 module-level HAIP_TEST_MODE (same as test_orthopedic.py)
Deferred nice-to-have: M1 color-mix, M4 Promise.all parallelize, M5 error escaping

# SDD Progress - UI å¥‘çº¦åŠ å›º

Plan: docs/superpowers/plans/2026-07-17-ui-contract-hardening.md
Base: aaff010

Task 1: complete (commit 052ddbb, review: spec OK; 3 'extras' adjudicated = session B2/B3 fixes, tests committed 773d517)
Audit fixes: #6 5caf535 / #7-#10 5a0e0d0 / #1#2#4 f4b7977 (guard citation 9415cc5, portal guard 0a00183)
Task 2: complete (commit a4e3bce, review: spec PASS 16/22 verifiable, quality PASS; 6 warn-items resolved by controller viaåç»­å…¨é‡ ruff/pytest è¿è¡Œ)
B6 fix: interventional_pain handler æ¼‚ç§» + 309 handler å¥‘çº¦æµ‹è¯• (5dfe5a9)
Task 3: complete (commit 7c4472b, review clean both verdicts)
Task 4: complete (commit 8ee4279, review: spec compliant; Important[C4è¯æ˜ç¼ºå¤±]ç”±controllerè¡¥è¯æ®é—­ç¯; Minor: FUNC_DEF_REä¸è¯†åˆ«ç®­å¤´å‡½æ•°(ä¸briefä¸€è‡´), mypy import-not-foundä¸ºæ—¢æœ‰æ¨¡å¼)
Task 5: complete (AGENTS.md é—¨ç¦ + ruff CI èŒƒå›´æ¸…é›¶; 9 ä¸ªå¤±è´¥ç¡®è®¤ä¸º d6f2c76 æ—¢æœ‰: 6 DemoPage + 3 togaf, å·²ç”¨ worktree åŸºçº¿å–è¯)
Final review: READY (0 Critical/Important; Minor: case_mgr æœªèµ°å…±äº«åŠ è½½å™¨ / launch_all æ˜¾å¼ç«¯å£ / scripts 15å¤„ç»å¯¹è·¯å¾„ â€” è®°ä¸ºåç»­ç¡¬åŒ–é¡¹)
Minor é—ç•™æ”¶å°¾: PATIENTS_FILE å•æº/launch_all ç«¯å£è§£æ + scripts 11 æ–‡ä»¶ç»å¯¹è·¯å¾„æ¸…é›¶ (36b0a46)
å­˜é‡å¤±è´¥æ¸…é›¶: DemoPage åŒæ­¥ (b100988) + togaf 3 æ–­è¨€ä¿®æ­£; å…¨é‡ 1555 passed / 0 failed

# SDD Progress - xhaip Ãâ°²×°×Ô°üº¬ (2026-08-02)
Plan: docs/superpowers/plans/2026-08-02-xhaip-self-contained.md
Branch: master (file-level commits; pre-existing WIP in tree)

- Task 1: sitecustomize.py ×Ô¾Ù - complete (commit 6e99048, review clean; Approved)
  - Minor deferred (plan-mandated): sys.path Ë³Ğò/dedup/È±Ê§Ä¿Â¼Ìø¹ıÎ´Ö±½Ó¶ÏÑÔ; scan ³£Á¿ÔÚ Task 7 ÆôÓÃ
  - Minor deferred: .pytest_cache WinError 183 warning Ïµ»·¾³²¢·¢ËùÖÂ (pre-existing), Task 8 È«Á¿ÅÜÊ±¸´ºË
- Task 2: test_antiemetic ËÀÂ·¾¶ÇåÀí - complete (commit 4ebb2ff, review clean; Approved)
  - Minor accepted: Ìá½»º¬Ô¤ÏÈ´æÔÚ WIP µÄµ¼Èë¸ñÊ½»¯ (ĞĞÎªµÈ¼Û, ÒÑºËÊµÊÇ¹¤×÷ÇøÔ­ÓĞ¸Ä¶¯); .pytest_cache warning È·ÈÏÏÈÓÚ±¾¸Ä¶¯´æÔÚ
- Task 3: 8 ¸ö SKILL.md Ïà¶ÔÂ·¾¶»¯ - complete (commit f3dff6b, review clean; Approved)
  - ¸´ºË: È«²Ö D:\FC ²ĞÁô½öÊ£ batch_md2.py / 2 ¸ö docs (Task 4-6 Ä¿±ê); packages/**/SKILL.md ÎŞ²ĞÁô
- Task 4: batch_md2 Íâ²¿Â·¾¶¿ÉÑ¡»¯ - complete (commit ca3a475, review clean; Approved)
  - ?? ÒÑ¸´ºË: ÎÄ¼şÔ­Îª untracked, Öğ¿é¶ÔÕÕ»á»°ÔçÆÚ¿ìÕÕ½ö 3 ´¦±à¼­
- Task 5: tools Ïà¶ÔÂ·¾¶»¯ - complete (commit 8b16abb, review clean; Approved)
  - Minor deferred (out-of-scope): ÒÑÈë¿âµÄ download.ps1 º¬ pre-existing Î²¶ººÅ (ĞĞ 75/156) ÓëÎŞ BOM µ¼ÖÂ PS5.1 ÎŞ·¨½âÎö - ½»×îÖÕÉó²é·ÖÕï
- Task 6: docs Á½´¦Â·¾¶ÇåÀí - complete (commit 6486210, review clean; Approved)
- Task 7: »Ø¹é·À»¤²âÊÔ - complete (commit 26a30dc, review clean; Approved)
  - ?? ÒÑ¸´ºË Task1 ¸¨Öú¶¨Òå: 6 Ä£Ê½Ë«Ğ±¸Ü±äÌåÆëÈ«, Ìø¹ı¼¯º¬ .superpowers/docs/superpowers
- Task 8: ÎÄµµ + È«Á¿ÑéÖ¤ - complete (commit f0a4d5e, review clean; Approved)
  - È«Á¿: 2543 passed / 55 failed (È«²¿ pre-existing WIP Æ¯ÒÆ, Óë±¾ÏµÁĞ 8 Ìá½»ÎÄ¼şÁãÖØµş) / 23 skipped; ruff clean; Ã°ÑÌ OK (¿ØÖÆÆ÷¶ÀÁ¢¸´ºË)
  - ÅĞ¶¨: 55 Ê§°Ü½ÓÊÜÎª pre-existing; ³É¹¦±ê×¼ÒÔ"ÎŞ±¾ÏµÁĞÒıÈë»Ø¹é"Îª×¼
- ×îÖÕÕûÌåÉó²é: MERGE_BASE=1932576, HEAD=f0a4d5e, 8 commits
- ×îÖÕÕûÌåÉó²é (1932576..f0a4d5e): With fixes - I1 download.ps1 ²»¿É½âÎö, I2 batch_md2 ÊØÎÀÈ±Ïİ (Path("").is_dir()=True ÒÑÊµÖ¤), I3 É¨Ãè²âÊÔÎ´½ø CI
- Fix batch (commit 857c8ac): 4 fixes, ¸´Éó Approved (Ë³Ğò¶ÏÑÔ·½ÏòĞŞÕıÕıÈ·)
- È«ÏµÁĞÍê³É: 9 commits 1932576..857c8ac, Éó²éÈ«ÂÌ
