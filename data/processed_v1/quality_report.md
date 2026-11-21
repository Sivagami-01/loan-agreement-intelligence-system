# Data quality report

- Documents checked: 18508
- Empty files (0 decoded characters): 0
- Tiny files (<5,000 decoded characters): 94
- Files with UTF-8 replacement characters: 1 (13 replacement characters)
- Boilerplate-only heuristic matches: 0
- Non-English heuristic matches: 0

Encoding is evaluated as streaming UTF-8-with-BOM decoding using replacement for malformed byte sequences; replacement-character counts are reported. Language labels are heuristic only: English uses common English function words, and non-English uses accented-letter/common non-English-word thresholds; remaining files are marked unknown. Boilerplate-only means fewer than 500 ASCII letters/digits remain in the first 100,000 decoded characters after HTML-tag removal; it is a screening heuristic, not a human judgment.

## Encoding-problem documents (first 100)

| doc_id | chars | language | encoding replacements |
|---|---:|---|---:|
| `000114/1144326/0001144326-11-000015_7.txt` | 461890 | English (heuristic) | 13 |

## Tiny documents (first 100)

| doc_id | chars | language | encoding replacements |
|---|---:|---|---:|
| `000000/3116/0000950137-07-016818_5.txt` | 2407 | English (heuristic) | 0 |
| `000000/6885/0000006885-00-000024_2.txt` | 2136 | English (heuristic) | 0 |
| `000002/21212/0000906555-06-000074_3.txt` | 4412 | English (heuristic) | 0 |
| `000002/24090/0001035704-04-000613_5.txt` | 3757 | English (heuristic) | 0 |
| `000003/33185/0001167966-04-000703_5.txt` | 4367 | English (heuristic) | 0 |
| `000003/33488/0001019056-09-000523_7.txt` | 2271 | English (heuristic) | 0 |
| `000003/38570/0001047469-04-006117_14.txt` | 4339 | English (heuristic) | 0 |
| `000005/52795/0000950123-11-035498_3.txt` | 4698 | English (heuristic) | 0 |
| `000005/54291/0000054291-02-000002_4.txt` | 2042 | English (heuristic) | 0 |
| `000005/54480/0001193125-11-187647_4.txt` | 2441 | English (heuristic) | 0 |
| `000005/54507/0000950130-02-004195_3.txt` | 4730 | English (heuristic) | 0 |
| `000006/69488/0000069488-06-000087_5.txt` | 2338 | English (heuristic) | 0 |
| `000007/75208/0000075208-11-000017_3.txt` | 2909 | English (heuristic) | 0 |
| `000008/86115/0001362310-09-001723_3.txt` | 3398 | English (heuristic) | 0 |
| `000008/89089/0001193125-16-492789_3.txt` | 4187 | English (heuristic) | 0 |
| `000010/102379/0000950134-05-012757_3.txt` | 4576 | English (heuristic) | 0 |
| `000010/102741/0000897101-05-000085_4.txt` | 1087 | English (heuristic) | 0 |
| `000010/105634/0000105634-16-000440_2.txt` | 3731 | English (heuristic) | 0 |
| `000010/106945/0000898430-96-001437_4.txt` | 4706 | English (heuristic) | 0 |
| `000010/109261/0000912057-99-005549_4.txt` | 3784 | English (heuristic) | 0 |
| `000010/109261/0001047469-98-040505_4.txt` | 3743 | English (heuristic) | 0 |
| `000010/109471/0000910680-07-000773_3.txt` | 4123 | English (heuristic) | 0 |
| `000020/201653/0001028212-05-000062_3.txt` | 4245 | English (heuristic) | 0 |
| `000035/350621/0001036050-00-001747_8.txt` | 4707 | English (heuristic) | 0 |
| `000035/350698/0001193125-11-334348_3.txt` | 4081 | English (heuristic) | 0 |
| `000035/356841/0001193125-08-141000_2.txt` | 1147 | English (heuristic) | 0 |
| `000035/356841/0001193125-08-141000_3.txt` | 1149 | English (heuristic) | 0 |
| `000072/720005/0000720005-15-000055_3.txt` | 1574 | English (heuristic) | 0 |
| `000072/724606/0000950137-04-004403_2.txt` | 4975 | English (heuristic) | 0 |
| `000072/724606/0000950137-04-004403_3.txt` | 4167 | English (heuristic) | 0 |
| `000074/740694/0000950124-03-002477_4.txt` | 2708 | English (heuristic) | 0 |
| `000074/746072/0000912057-96-029338_5.txt` | 897 | English (heuristic) | 0 |
| `000075/752642/0000752642-13-000005_3.txt` | 3154 | English (heuristic) | 0 |
| `000075/753048/0001047469-98-030374_3.txt` | 4765 | English (heuristic) | 0 |
| `000075/753048/0001047469-98-030374_5.txt` | 4656 | English (heuristic) | 0 |
| `000078/787784/0000950144-98-003927_6.txt` | 4384 | English (heuristic) | 0 |
| `000078/787784/0000950144-98-003927_7.txt` | 4688 | English (heuristic) | 0 |
| `000079/791450/0000912057-97-016417_2.txt` | 2779 | English (heuristic) | 0 |
| `000079/795665/0000950137-03-004407_4.txt` | 4723 | English (heuristic) | 0 |
| `000079/796502/0000910647-00-500041_2.txt` | 4705 | English (heuristic) | 0 |
| `000080/801622/0000898822-96-000074_2.txt` | 2405 | English (heuristic) | 0 |
| `000080/804888/0001193125-04-132497_3.txt` | 3466 | English (heuristic) | 0 |
| `000080/808450/0000808450-07-000010_3.txt` | 2582 | English (heuristic) | 0 |
| `000080/808450/0000950137-07-008895_3.txt` | 1820 | English (heuristic) | 0 |
| `000082/821361/0000912057-97-027552_2.txt` | 4381 | English (heuristic) | 0 |
| `000082/821361/0001047469-97-004531_2.txt` | 2818 | English (heuristic) | 0 |
| `000083/834162/0001104659-10-015416_3.txt` | 2294 | English (heuristic) | 0 |
| `000084/844161/0001104659-11-009307_3.txt` | 3544 | English (heuristic) | 0 |
| `000084/844161/0001104659-11-068439_3.txt` | 4062 | English (heuristic) | 0 |
| `000084/844161/0001104659-11-068439_4.txt` | 4061 | English (heuristic) | 0 |
| `000084/847074/0001035704-00-000689_3.txt` | 3249 | English (heuristic) | 0 |
| `000085/854852/0000912057-00-050950_7.txt` | 3082 | English (heuristic) | 0 |
| `000085/854852/0000912057-00-050950_8.txt` | 3040 | English (heuristic) | 0 |
| `000085/854852/0000912057-00-050950_9.txt` | 3044 | English (heuristic) | 0 |
| `000088/880115/0001104659-02-000948_3.txt` | 3834 | English (heuristic) | 0 |
| `000088/882289/0000882289-04-000059_3.txt` | 2401 | English (heuristic) | 0 |
| `000088/883476/0001193125-03-037807_12.txt` | 4759 | English (heuristic) | 0 |
| `000088/883558/0000912057-97-005971_13.txt` | 3792 | English (heuristic) | 0 |
| `000088/883558/0000912057-97-005971_14.txt` | 4196 | English (heuristic) | 0 |
| `000088/883558/0001047469-98-021380_5.txt` | 4410 | English (heuristic) | 0 |
| `000088/883558/0001047469-98-021380_6.txt` | 4475 | English (heuristic) | 0 |
| `000088/883943/0000897101-96-000504_4.txt` | 3326 | English (heuristic) | 0 |
| `000088/883977/0000950144-04-008742_2.txt` | 4567 | English (heuristic) | 0 |
| `000088/885550/0000950124-03-001987_3.txt` | 2647 | English (heuristic) | 0 |
| `000088/885550/0000950124-04-002762_2.txt` | 2688 | English (heuristic) | 0 |
| `000088/887905/0001104659-05-053404_3.txt` | 1510 | English (heuristic) | 0 |
| `000088/887905/0001104659-11-020933_3.txt` | 1892 | English (heuristic) | 0 |
| `000089/891329/0001047469-98-027229_6.txt` | 4561 | English (heuristic) | 0 |
| `000089/893741/0001104659-02-003097_3.txt` | 4936 | English (heuristic) | 0 |
| `000089/895651/0000950135-97-001118_3.txt` | 4108 | English (heuristic) | 0 |
| `000089/895651/0000950135-97-001118_4.txt` | 4137 | English (heuristic) | 0 |
| `000089/896985/0000950115-98-000947_5.txt` | 2491 | English (heuristic) | 0 |
| `000089/898173/0000898173-98-000009_4.txt` | 4464 | English (heuristic) | 0 |
| `000090/908440/0000950133-04-000043_3.txt` | 4503 | English (heuristic) | 0 |
| `000091/913666/0000950154-01-500170_3.txt` | 3256 | English (heuristic) | 0 |
| `000091/919640/0000950137-98-001137_2.txt` | 2734 | English (heuristic) | 0 |
| `000092/927003/0000950134-05-010826_2.txt` | 4927 | English (heuristic) | 0 |
| `000092/929940/0001104659-05-022189_6.txt` | 4788 | English (heuristic) | 0 |
| `000093/937289/0000891020-98-001428_3.txt` | 3333 | English (heuristic) | 0 |
| `000094/943897/0001193125-06-151084_4.txt` | 2885 | English (heuristic) | 0 |
| `000100/1000209/0001193125-05-162572_2.txt` | 2781 | English (heuristic) | 0 |
| `000102/1029506/0001015402-01-503083_3.txt` | 2258 | English (heuristic) | 0 |
| `000103/1039684/0000930661-02-003368_4.txt` | 2114 | English (heuristic) | 0 |
| `000104/1042431/0001012870-01-501570_5.txt` | 3814 | English (heuristic) | 0 |
| `000104/1046212/0000950129-05-005632_20.txt` | 4388 | English (heuristic) | 0 |
| `000104/1047202/0001193125-08-127876_2.txt` | 4167 | English (heuristic) | 0 |
| `000107/1070523/0000950124-05-006849_2.txt` | 3031 | English (heuristic) | 0 |
| `000107/1070523/0000950124-06-005156_2.txt` | 2999 | English (heuristic) | 0 |
| `000107/1077688/0000916641-03-001030_6.txt` | 3812 | English (heuristic) | 0 |
| `000109/1094365/0001085037-03-000795_4.txt` | 2690 | English (heuristic) | 0 |
| `000114/1142701/0001047469-04-036151_2.txt` | 4664 | English (heuristic) | 0 |
| `000116/1168335/0001193125-04-040712_3.txt` | 4167 | English (heuristic) | 0 |
| `000117/1171500/0000950123-05-012468_4.txt` | 3957 | English (heuristic) | 0 |
| `000132/1325281/0001104659-08-039898_3.txt` | 4076 | English (heuristic) | 0 |

## Boilerplate-only heuristic matches (first 100)

| doc_id | chars | language | encoding replacements |
|---|---:|---|---:|

## Non-English heuristic matches (first 100)

| doc_id | chars | language | encoding replacements |
|---|---:|---|---:|

## 20 shortest documents

| doc_id | chars | language | encoding replacements |
|---|---:|---|---:|
| `000074/746072/0000912057-96-029338_5.txt` | 897 | English (heuristic) | 0 |
| `000010/102741/0000897101-05-000085_4.txt` | 1087 | English (heuristic) | 0 |
| `000035/356841/0001193125-08-141000_2.txt` | 1147 | English (heuristic) | 0 |
| `000035/356841/0001193125-08-141000_3.txt` | 1149 | English (heuristic) | 0 |
| `000088/887905/0001104659-05-053404_3.txt` | 1510 | English (heuristic) | 0 |
| `000072/720005/0000720005-15-000055_3.txt` | 1574 | English (heuristic) | 0 |
| `000080/808450/0000950137-07-008895_3.txt` | 1820 | English (heuristic) | 0 |
| `000088/887905/0001104659-11-020933_3.txt` | 1892 | English (heuristic) | 0 |
| `000005/54291/0000054291-02-000002_4.txt` | 2042 | English (heuristic) | 0 |
| `000103/1039684/0000930661-02-003368_4.txt` | 2114 | English (heuristic) | 0 |
| `000000/6885/0000006885-00-000024_2.txt` | 2136 | English (heuristic) | 0 |
| `000102/1029506/0001015402-01-503083_3.txt` | 2258 | English (heuristic) | 0 |
| `000003/33488/0001019056-09-000523_7.txt` | 2271 | English (heuristic) | 0 |
| `000083/834162/0001104659-10-015416_3.txt` | 2294 | English (heuristic) | 0 |
| `000006/69488/0000069488-06-000087_5.txt` | 2338 | English (heuristic) | 0 |
| `000088/882289/0000882289-04-000059_3.txt` | 2401 | English (heuristic) | 0 |
| `000080/801622/0000898822-96-000074_2.txt` | 2405 | English (heuristic) | 0 |
| `000000/3116/0000950137-07-016818_5.txt` | 2407 | English (heuristic) | 0 |
| `000005/54480/0001193125-11-187647_4.txt` | 2441 | English (heuristic) | 0 |
| `000089/896985/0000950115-98-000947_5.txt` | 2491 | English (heuristic) | 0 |

## 20 longest documents

| doc_id | chars | language | encoding replacements |
|---|---:|---|---:|
| `000146/1467858/0001193125-10-261749_4.txt` | 6983062 | English (heuristic) | 0 |
| `000146/1467858/0001193125-09-169233_10.txt` | 6717928 | English (heuristic) | 0 |
| `000130/1304280/0000950123-11-009997_4.txt` | 5013847 | English (heuristic) | 0 |
| `000130/1304280/0000950123-11-009997_5.txt` | 4239959 | English (heuristic) | 0 |
| `000010/102379/0000102379-10-000027_3.txt` | 3457351 | English (heuristic) | 0 |
| `000001/19520/0000912057-97-007442_2.txt` | 2451687 | English (heuristic) | 0 |
| `000000/9389/0000009389-11-000014_3.txt` | 2401602 | English (heuristic) | 0 |
| `000127/1279228/0000950116-04-000434_6.txt` | 2363677 | English (heuristic) | 0 |
| `000130/1304280/0000950123-09-051624_2.txt` | 2158526 | English (heuristic) | 0 |
| `000087/874016/0000950123-10-070185_2.txt` | 2110445 | English (heuristic) | 0 |
| `000149/1498209/0001193125-10-244236_4.txt` | 2091471 | English (heuristic) | 0 |
| `000159/1599489/0001193125-14-259659_4.txt` | 2033891 | English (heuristic) | 0 |
| `000091/916457/0000916457-10-000035_2.txt` | 1938680 | English (heuristic) | 0 |
| `000079/791519/0001104659-16-093303_3.txt` | 1871547 | English (heuristic) | 0 |
| `000079/791519/0001104659-16-093302_3.txt` | 1871547 | English (heuristic) | 0 |
| `000134/1344154/0001104659-11-032611_11.txt` | 1870663 | English (heuristic) | 0 |
| `000076/766738/0000950133-96-000195_2.txt` | 1863730 | English (heuristic) | 0 |
| `000112/1128928/0000950144-01-500428_9.txt` | 1806688 | English (heuristic) | 0 |
| `000071/718789/0001437749-11-000225_2.txt` | 1777175 | English (heuristic) | 0 |
| `000130/1304280/0000950123-09-051624_3.txt` | 1773893 | English (heuristic) | 0 |
