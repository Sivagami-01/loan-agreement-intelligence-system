# Page-class calibration samples

Seed: `42`. Current rule and letter-only rule use the exact same expected-script denominator (alphabetic characters only); the implementation already excludes digits, whitespace, punctuation, and symbols from this denominator. Thus those two class counts match.

| Parsed file | Pages | Current GOOD/SUSPICIOUS/BAD | Letter-only GOOD/SUSPICIOUS/BAD | Proposed GOOD/SUSPICIOUS/BAD |
|---|---:|---:|---:|---:|
| `03_dbs_mitc.json` | 2 | 2/0/0 | 2/0/0 | 2/0/0 |
| `04_dbs_mitc-ahl.json` | 4 | 4/0/0 | 4/0/0 | 4/0/0 |
| `06_clix_10.-CHFL_Policy-on-Interest-Rate-MITC-27May2025.json` | 11 | 11/0/0 | 11/0/0 | 11/0/0 |
| `09_muthoothomefin_MHIL-MITC.json` | 7 | 7/0/0 | 7/0/0 | 7/0/0 |
| `11_gichfindia_MOST-IMPORTANT-TERMS-1.json` | 5 | 5/0/0 | 5/0/0 | 5/0/0 |
| `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.json` | 42 | 22/14/6 | 22/14/6 | 35/1/6 |
| `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.json` | 29 | 1/23/5 | 1/23/5 | 19/5/5 |
| `14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi.json` | 29 | 2/22/5 | 2/22/5 | 19/5/5 |
| `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json` | 31 | 1/24/6 | 1/24/6 | 15/10/6 |
| `16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1_.json` | 31 | 14/14/3 | 14/14/3 | 26/2/3 |
| `17_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Bengali.json` | 33 | 9/19/5 | 9/19/5 | 26/2/5 |
| `personal_business_loan_agreement.json` | 16 | 14/0/2 | 14/0/2 | 14/0/2 |

Current total: 92 GOOD, 116 SUSPICIOUS, 32 BAD.
Letter-only total: 92 GOOD, 116 SUSPICIOUS, 32 BAD (same denominator as current code).
Proposed total (0.10/0.30/0.65): 183 GOOD, 25 SUSPICIOUS, 32 BAD.

## Random examples

Each class has 10 examples selected without replacement using seed 42. Expected-script share and Latin letter share use alphabetic characters as denominator. Non-alphanumeric ratio uses all extracted characters. The symbol ratio matches the existing classifier metric (non-whitespace characters, combining marks excluded). For GOOD pages, PNGs are newly rendered in `review_images/good_samples/`; other samples use `review_images/`.

### GOOD (10 samples)
- **File:** `personal_business_loan_agreement.json`; **page:** 4; **class:** GOOD; **proposed:** GOOD; **expected script:** unknown.
  **Metrics:** expected-script share `n/a`; Latin letter share `1.0000`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.2077`; symbol ratio `0.0385`; letters `5165`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/good_samples/personal_business_loan_agreement_page_0004.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `Page 2 of 14 2/12 2/12 TC[PHONE/NUMBER REDACTED] appropriation thereof into principal and interest. The payment of all the monies by the Borrower including EMIs shall  be made on or before the respective due dates, at such place as the Bank may require, without any set-off or coun- terclaim or withholding`
- **File:** `06_clix_10.-CHFL_Policy-on-Interest-Rate-MITC-27May2025.json`; **page:** 9; **class:** GOOD; **proposed:** GOOD; **expected script:** unknown.
  **Metrics:** expected-script share `n/a`; Latin letter share `1.0000`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.2928`; symbol ratio `0.0479`; letters `1027`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/good_samples/06_clix_10.-CHFL_Policy-on-Interest-Rate-MITC-27May2025_page_0009.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `      Page 9 of 11  Public & Non Confidential Information  Public & Non Confidential Information  (Housing/ Extension/  improvement/  Refinance (Balance  Transfer)/Plot purchase  + construction)    change     8     Switching from Fixed to  Variable Rate Loan  (Housing/ Extension/  improvement/  Refi`
- **File:** `04_dbs_mitc-ahl.json`; **page:** 2; **class:** GOOD; **proposed:** GOOD; **expected script:** unknown.
  **Metrics:** expected-script share `n/a`; Latin letter share `1.0000`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.2033`; symbol ratio `0.0285`; letters `5234`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/good_samples/04_dbs_mitc-ahl_page_0002.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `2 MOST IMPORTANT TERMS AND CONDITIONS (MITC) VIII. Loan Drawdown / Disbursement The Loan (or any part thereof) may be disbursed by the Lender upon receiving a drawdown request from the Borrower.  The entire Loan Amount should be availed of within the Availability Period specified by the Lender. The `
- **File:** `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.json`; **page:** 17; **class:** GOOD; **proposed:** GOOD; **expected script:** malayalam.
  **Metrics:** expected-script share `0.4320`; Latin letter share `0.5680`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.3655`; symbol ratio `0.0306`; letters `1602`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/good_samples/12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam_page_0017.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `          Page 17 of 42  ഉപഭ ാക്താവ ന്  നൽക ിം.  ഏല്റ്റട ക്കൽ/ബാലൻസ്  പ്ടാൻസ്ൈർ  വായ്പകള ല്ട  കാരയത്ത ൽ, തലല്ക്കട്ട്, ല ങ്ക് ഭരഖകള ല്ട ഭൈാഭട്ടാഭകാപ്പ ക്കായ ള്ള ഉപഭ ാക്താവ ന്ല്റ  അഭപക്ഷ ഫകമാറ ന്ന ബാങ്ക്/സാമ്പത്ത ക സ്ഥാപനത്ത ൽ ന ന്ന് തലല്ക്കട്ട്, ല ങ്ക് ഭരഖകൾ  ല  ക്ക ന്നത ന് വ ഭധയമായ  സ ഗമമാക്ക ിം.   `
- **File:** `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.json`; **page:** 10; **class:** GOOD; **proposed:** GOOD; **expected script:** malayalam.
  **Metrics:** expected-script share `0.4546`; Latin letter share `0.5454`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.3805`; symbol ratio `0.0284`; letters `1498`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/good_samples/12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam_page_0010.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `          Page 10 of 42  •  Top up loans for Business Purpose / Use such as Working Capital, Debt Consolidation,  Repayment of Business Loan, Expansion of business, Acquisition of Business asset or any similar  end usage of funds.  ബ സ നസ് ഉഭേശയത്ത നായ ള്ള ഭടാപ്പ് അപ്പ് വായ്പകൾ / പ്പവർത്തന മൂലധനിം, `
- **File:** `11_gichfindia_MOST-IMPORTANT-TERMS-1.json`; **page:** 5; **class:** GOOD; **proposed:** GOOD; **expected script:** unknown.
  **Metrics:** expected-script share `n/a`; Latin letter share `1.0000`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.2311`; symbol ratio `0.0431`; letters `1610`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/good_samples/11_gichfindia_MOST-IMPORTANT-TERMS-1_page_0005.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `GIC HOUSING FINANCE LTD    Regd Address: National Insurance Bldg, 6th floor, J.T.Road, Churchgate, Mumabai-400020 Page 5    9.2. Borrower can meet or write to the Sr. Vice President of the respective location address or  Email ID as provided in our website www.gichfindia.com  9.3. In case the concer`
- **File:** `09_muthoothomefin_MHIL-MITC.json`; **page:** 1; **class:** GOOD; **proposed:** GOOD; **expected script:** unknown.
  **Metrics:** expected-script share `n/a`; Latin letter share `1.0000`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.2525`; symbol ratio `0.0792`; letters `2818`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/good_samples/09_muthoothomefin_MHIL-MITC_page_0001.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `    THE MOST IMPORTANT TERMS AND CONDITIONS (MITC)      The Most Important Terms and Conditions (MITC) of the loan between the Borrower/s Mr. / Mrs. and Muthoot Homefin (India) Ltd.,  hereinafter called “MHIL” are mentioned below.    1.  Loan Details    a.  Application Form No.    b.  Purpose of Loa`
- **File:** `06_clix_10.-CHFL_Policy-on-Interest-Rate-MITC-27May2025.json`; **page:** 8; **class:** GOOD; **proposed:** GOOD; **expected script:** unknown.
  **Metrics:** expected-script share `n/a`; Latin letter share `1.0000`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.3137`; symbol ratio `0.0345`; letters `1151`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/good_samples/06_clix_10.-CHFL_Policy-on-Interest-Rate-MITC-27May2025_page_0008.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `      Page 8 of 11  Public & Non Confidential Information  Public & Non Confidential Information    10. Fee and Charges  As detailed in the list below:    Sr.     No.    Name of the Product/  Service     Name of Fee/  Charge Levied     When Payable     Frequency    Amount in Rupees   1     Fee for H`
- **File:** `personal_business_loan_agreement.json`; **page:** 9; **class:** GOOD; **proposed:** GOOD; **expected script:** unknown.
  **Metrics:** expected-script share `n/a`; Latin letter share `1.0000`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.3461`; symbol ratio `0.1325`; letters `1008`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/good_samples/personal_business_loan_agreement_page_0009.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `Page 7 of 14     POST DATED CHEQUE ACKNOWLEDGEMENT LETTER Mention the count of cheque received Drawee Bank    Bank Account No.    MICR code    Cheque  Branch    Cheque  City    Cheque No.    Cheque Date    Cheque  Amount    From  To  From  To              Cheque Received  (A)Cheques Dated    (B)Cheq`
- **File:** `17_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Bengali.json`; **page:** 6; **class:** GOOD; **proposed:** GOOD; **expected script:** bengali.
  **Metrics:** expected-script share `0.4117`; Latin letter share `0.5883`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.3368`; symbol ratio `0.0349`; letters `2264`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/good_samples/17_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Bengali_page_0006.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `          Page 6 of 33    গ্রাহকরা কপটিন্ট কগেওট়ে বযতীত অন্য ককাটন্া িাযযটি অথতপ্রদান্ করটি (অথতাৎ লরট়েি োইি গ্রস  কসটেিটিন্ট/ন্যাশন্াি ইটিকট্রলন্ক ফাড ট্রান্সফার/ইলিলডট়েে কপটিন্ট সালভতস/ইউলন্ফাইড কপটিন্ট ইন্টারটফস  ইতযালদ): ককাম্পালন্র স্পষ্ট তহলবি প্রালির পর ঋণ অযাকাউটন্ট জিা করা হটব, (সাযারণত`

### SUSPICIOUS (10 samples)
- **File:** `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.json`; **page:** 33; **class:** SUSPICIOUS; **proposed:** GOOD; **expected script:** malayalam.
  **Metrics:** expected-script share `0.3979`; Latin letter share `0.6021`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.3412`; symbol ratio `0.0316`; letters `1307`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam_page_0033.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `          Page 33 of 42  Crores  >250 പകാടി രൂരയിൽ  നിന്ന് 500 പകാടി രൂര  വപ്പര  > 500 Crores  >500 പകാടി രൂരയിൽ  കൂട തൽ  [PHONE/NUMBER REDACTED],000/-  Note: The charges stated above will not be levied on loans that are extended exclusively for the  payment of fees and charges related to the loan.  ക `
- **File:** `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json`; **page:** 24; **class:** SUSPICIOUS; **proposed:** GOOD; **expected script:** gurmukhi.
  **Metrics:** expected-script share `0.3233`; Latin letter share `0.6767`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.3770`; symbol ratio `0.0475`; letters `1534`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1__page_0024.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `        Page 24 of 31        The Charges mentioned above are as applicable on the date of signing this MITC. These charges are  subject to modification and the revised charges as mentioned on the Company’s website  (https://www.bajajhousingfinance.in/) will be applicable. The Borrower agrees that al`
- **File:** `14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi.json`; **page:** 25; **class:** SUSPICIOUS; **proposed:** GOOD; **expected script:** devanagari.
  **Metrics:** expected-script share `0.3315`; Latin letter share `0.6685`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.3801`; symbol ratio `0.0383`; letters `1463`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi_page_0025.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `                               Page 25 of 29    Sr.  No.  िमांक Material terms and  conditions   महत्वपूर्ण तियम व शिें  Trigger  point   टट्गर बबिदु  Charge levy /  discontinuation   शुल्क लगािा/बंद करिा  CPC (chargeable per  month) *  सीपीसी (प्रति माह शुल्क लागू) *  (Rs.)   (रु.)  प्रतितिथधत्व, व`
- **File:** `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.json`; **page:** 18; **class:** SUSPICIOUS; **proposed:** GOOD; **expected script:** malayalam.
  **Metrics:** expected-script share `0.3827`; Latin letter share `0.6173`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.3567`; symbol ratio `0.0423`; letters `946`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam_page_0018.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `          Page 18 of 42  2  [EMAIL REDACTED]    Alternatively, the customers may write to The Head of Customer Experience at:  Bajaj Housing Finance Limited,  5th Floor, B2 Cerebrum IT Park,  Kumar City Kalyani Nagar Pune,  Maharashtra Pin – [PHONE/NUMBER REDACTED] ദ വസത്ത ന ള്ള ൽ ല്ലവൽ`
- **File:** `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.json`; **page:** 16; **class:** SUSPICIOUS; **proposed:** GOOD; **expected script:** malayalam.
  **Metrics:** expected-script share `0.3360`; Latin letter share `0.6640`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.3275`; symbol ratio `0.0296`; letters `1524`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam_page_0016.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `          Page 16 of 42  Fair Practice code of the company can be referred online in link provided below:  കമ്പന യ ല്ട നയായമായ പ്പാക്ടീസ് ഭകാ് താല്ഴ നൽക യ ര ക്ക ന്ന ല ങ്ക ൽ  ഓൺഫലന ൽ പരാമർശ ക്കാവ ന്നതാണ്:    https://www.bajajhousingfinance.in/notice-board    14.  CUSTOMER SERVICES / ഉരപഭാക്തൃ പസവനങ്ങ`
- **File:** `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.json`; **page:** 20; **class:** SUSPICIOUS; **proposed:** GOOD; **expected script:** devanagari.
  **Metrics:** expected-script share `0.3449`; Latin letter share `0.6551`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.4320`; symbol ratio `0.0312`; letters `1435`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi_page_0020.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `                               Page 20 of 29    18  Flexi  Annual  Maintenance  Charge  –  Flexi  Hybrid Loan   फ्िेक् ी एनुअि िेंटेनें   शुलक - फ्िेक् ी हाइनब्ड  िोन  Annual  Maintenanc e Charge   िार्षिंक  रिरिाि शुलक  Applicable  on  Flexi  Hybrid  Loan  फ्िेक् ी  हाइनब्ड िोन  पर िागू  Annual  Ch`
- **File:** `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.json`; **page:** 22; **class:** SUSPICIOUS; **proposed:** GOOD; **expected script:** devanagari.
  **Metrics:** expected-script share `0.3254`; Latin letter share `0.6746`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.4539`; symbol ratio `0.1048`; letters `925`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi_page_0022.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `                               Page 22 of 29    गर्िा की जािी है, जैसा तक िीचे दी गई िाथलका में बिाया गया है. प्राप्प्ि के आधार पर एलपीसी की  गर्िा की जाएगी. इि शुल्कों को पूंजीकृि िहीं तकया जाएगा.    Sanctioned Loan Amount  (For loans sanctioned on or after  July 01, 2026)    स्वीकृि लोि राशश  (01 `
- **File:** `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json`; **page:** 10; **class:** SUSPICIOUS; **proposed:** GOOD; **expected script:** gurmukhi.
  **Metrics:** expected-script share `0.3324`; Latin letter share `0.6676`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.4247`; symbol ratio `0.0229`; letters `1715`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1__page_0010.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `        Page 10 of 31      o  The construction carried out over the Property/ies has been undertaken as per the approved  plans and as per applicable laws/bye-laws/rules and regulations;  ਜਾਇਦਾਦ/ਜਾਇਦਾਦਾਾਂ ਉਿੱਤੇ ਿੀਤੀ ਿਈ ਉ ਾਿੀ ਿਨਜ਼਼ੂਿਸ਼ੁਦਾ ਯੋਜਨਾਿਾਾਂ ਦੇ ਅਨੁ ਾਿ ਅਤੇ ਲ ਿ ਕਾਨ਼ੂਿੰਨਾਾਂ/ਉਪ-ਕਾਨ਼ੂਿੰਨਾਾਂ/ਸਨਯਿਾਾਂ`
- **File:** `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json`; **page:** 26; **class:** SUSPICIOUS; **proposed:** GOOD; **expected script:** gurmukhi.
  **Metrics:** expected-script share `0.3523`; Latin letter share `0.6477`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.4228`; symbol ratio `0.0448`; letters `880`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1__page_0026.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `        Page 26 of 31      Sr.  No.  Material terms and  conditions  ਮ਼ੁਿੱਖ ਨਨਯਮ ਅਤੇ ਸ਼ਰਤ ਾਂ    Trigger point  ਟਨਰੱਗਰ ਪੁਆਇੰਟ    Charge levy / discontinuation  ਚ ਰਜ ਲਗ ਉਣ  / ਬੂੰਦ ਕਰਨ     CPC (chargeable per  month) *  **CPC (ਪਰਤ਼ੀ ਮਹ਼ੀਨ਼ੇ  ਚ ਰਜਯੋਗ) ***  (Rs.)   (ਰ਼ੁ.)  ਮਹ਼ੀਨ਼ੇ    4  Non-submission of`
- **File:** `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json`; **page:** 19; **class:** SUSPICIOUS; **proposed:** SUSPICIOUS; **expected script:** gurmukhi.
  **Metrics:** expected-script share `0.2682`; Latin letter share `0.7318`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.4401`; symbol ratio `0.0550`; letters `906`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1__page_0019.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `        Page 19 of 31      Sr.  No.  ਕ੍ਰਮ  ਸੰਨਿ ਆ  Nature of Fee/  Charge  ਫੀਸ / ਚ ਰਜ ਦੀ  ਪਰਨਕਰਤ਼ੀ  Name of  Fee/ Charge  ਫੀਸ / ਚ ਰਜ ਦ   ਨ ਮ  When  Payable  ਕਦੋਂ ਅਦ ਇਗ਼ੀ  Frequency  ਬ ਰੰਬ ਰਤ   Amount   ਰਕਮ  loan/ Flexi Hybrid  loan)    ਿੌਜ਼ੂਦਾ ਲੋਨ ਨ ੂੰ ਨਵੇਂ ਉਤਪਾਦ  ਜਵਿੱਚ ਤਬਦੀਿੀ (ਟਿਿ ਲੋਨ  / ਫਿੈਕ ੀ ਟਿਿ`

### BAD (10 samples)
- **File:** `14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi.json`; **page:** 2; **class:** BAD; **proposed:** BAD; **expected script:** devanagari.
  **Metrics:** expected-script share `0.3364`; Latin letter share `0.6636`; private-use count `6`; `(cid:...)` count `0`; non-alphanumeric ratio `0.4279`; symbol ratio `0.0740`; letters `1412`; flags `{'pua': 6, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi_page_0002.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `                               Page 2 of 29    *The EMI is indicative and may be subject to changes depending on factors, including  but not limited to, the date of disbursement, actual loan amount being utilized and  the stage of construction of the collateral. A system generated repayment schedule`
- **File:** `16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1_.json`; **page:** 1; **class:** BAD; **proposed:** BAD; **expected script:** bengali.
  **Metrics:** expected-script share `0.4017`; Latin letter share `0.5983`; private-use count `6`; `(cid:...)` count `0`; non-alphanumeric ratio `0.3769`; symbol ratio `0.0638`; letters `1633`; flags `{'pua': 6, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1__page_0001.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `          Page 1 of 31    MOST IMPORTANT TERMS AND CONDITIONS (MITC)  সর্বাধিক গুরুত্বপূর্ব শর্বার্লী (MITC)    Pursuant to the terms and conditions agreed to between BAJAJ HOUSING FINANCE LIMITED ("BHFL" or "the  Lender") and the Borrower ("the Borrower" or "the Customer") as detailed in the Sancti`
- **File:** `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json`; **page:** 12; **class:** BAD; **proposed:** BAD; **expected script:** gurmukhi.
  **Metrics:** expected-script share `0.3532`; Latin letter share `0.6468`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.4223`; symbol ratio `0.0353`; letters `1223`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': True}`.
  **PNG:** `data/processed/review_images/15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1__page_0012.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `        Page 12 of 31      ਆਪਣੇ ਇਕੱਿੇ ਸਿਿੇਕ ਤੇ, ਉਧਾਿ ਲੈਣ ਵ ਲੇ ਦ  ਨ ਮ, ਪਤ , ਫੋਟੋ,  ੁਿੱਸਖਆ ਿੇਿਿੇ (ਜੇਕਿ ਲ ਿ ਹੋਵੇ) ਅਤੇ ਅਸਜਹੀ ਹੋਿ ਜਾਣਕਾਿੀ ਪਰਕਾਸਸ਼ਤ  ਕਿਨਾ ਜਜਵੇਂ ਬਜਾਜ ਹਾਊਸ ਿੰਗ ਫਾਈਨੈਂ  ਸਿਸਿਟੇਡ ਉਸਚਤ  ਿਝੇ, ਇਿੈਕਟਰਾਸਨਕ, ਸਪਰਿੰਟ ਅਤੇ  ੋਸ਼ਿ ਿੀਡੀਆ ਜਵਿੱਚ, ਅਤੇ ਅਸਜਹੇ ਪਰਕਾਸ਼ਨ ਜਵਿੱਚ  ਅਸਜਹੇ ਸਡਫਾਿਟ ਘਟਨਾ ਦੀ ਿਿੱਲ ਵੀ ਸ਼ਾਿਿ ਹੋਿ`
- **File:** `personal_business_loan_agreement.json`; **page:** 12; **class:** BAD; **proposed:** BAD; **expected script:** unknown.
  **Metrics:** expected-script share `n/a`; Latin letter share `1.0000`; private-use count `0`; `(cid:...)` count `0`; non-alphanumeric ratio `0.2857`; symbol ratio `0.0000`; letters `6`; flags `{'pua': 0, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/personal_business_loan_agreement_page_0012.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `Page 10 of 14 `
- **File:** `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json`; **page:** 2; **class:** BAD; **proposed:** BAD; **expected script:** gurmukhi.
  **Metrics:** expected-script share `0.2598`; Latin letter share `0.7402`; private-use count `6`; `(cid:...)` count `0`; non-alphanumeric ratio `0.4378`; symbol ratio `0.1022`; letters `1320`; flags `{'pua': 6, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1__page_0002.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `        Page 2 of 31      2. EMI AMOUNT* (in Rs.): ________           ਈ.ਐਮ.ਆਈ ਰਕਮ* (ਰੁਨਪਆਾਂ ਵਵਿੱਚ): ________    *The EMI is indicative and may be subject to changes depending on factors, including but not  limited to, the date of disbursement, actual loan amount being utilized and the stage of  cons`
- **File:** `14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi.json`; **page:** 3; **class:** BAD; **proposed:** BAD; **expected script:** devanagari.
  **Metrics:** expected-script share `0.2567`; Latin letter share `0.7433`; private-use count `3`; `(cid:...)` count `0`; non-alphanumeric ratio `0.3677`; symbol ratio `0.0673`; letters `1722`; flags `{'pua': 3, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi_page_0003.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `                               Page 3 of 29    Applicable Annualized Rate  of Interest  िागू िार्षिंक ब्याज दर  Fixed Rate of Interest during Fixed Rate Tenure followed by Floating  Rate of Interest during Floating Rate Tenure  नफक्स्ड रेट की अिमध के दौरान ब्याज की नफक्स्ड दर और उ के बाद फ्िोटटिंग र`
- **File:** `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.json`; **page:** 2; **class:** BAD; **proposed:** BAD; **expected script:** devanagari.
  **Metrics:** expected-script share `0.3353`; Latin letter share `0.6647`; private-use count `6`; `(cid:...)` count `0`; non-alphanumeric ratio `0.4280`; symbol ratio `0.0722`; letters `1378`; flags `{'pua': 6, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi_page_0002.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `                               Page 2 of 29    *The EMI is indicative and may be subject to changes depending on factors, including  but not limited to, the date of disbursement, actual loan amount being utilized and  the stage of construction of the collateral. A system generated repayment schedule`
- **File:** `14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi.json`; **page:** 5; **class:** BAD; **proposed:** BAD; **expected script:** devanagari.
  **Metrics:** expected-script share `0.2842`; Latin letter share `0.7158`; private-use count `6`; `(cid:...)` count `0`; non-alphanumeric ratio `0.4137`; symbol ratio `0.0632`; letters `1214`; flags `{'pua': 6, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi_page_0005.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `                               Page 5 of 29      4. LOAN TENURE/ लोि की अवथध: ____ months / िहीने      Dual rate / दोहरी दर:   Fixed Rate Tenure / नफक्स्ड दर कायाकाि  __ months / िहीने  Floating Rate Tenure / फ्िोटटिंग दर कायाकाि __ months / िहीने    Note: ‘Loan Tenure' mentioned above is inclusive `
- **File:** `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json`; **page:** 3; **class:** BAD; **proposed:** BAD; **expected script:** gurmukhi.
  **Metrics:** expected-script share `0.2391`; Latin letter share `0.7598`; private-use count `3`; `(cid:...)` count `0`; non-alphanumeric ratio `0.4788`; symbol ratio `0.1743`; letters `845`; flags `{'pua': 3, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1__page_0003.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `        Page 3 of 31      Floating Rate of  Interest       ਭਿ FRR ਨ ਲ ਜ ੜੀ ਫਿੋਸਟਿੰਗ  ਸਿਆਜ ਦਿ  Interest  _______% + _______% = _______% per  annum     ਭਿ FRR +  ਪਰੈਡ = ਲ ਿ ਫਿੋਸਟਿੰਗ ਸਿਆਜ ದਿ  _______% + _______% = _______%  ਾਿਾਨਾ  Fixed Rate of Interest    ਸਫਕ ਡ ਸਿਆਜ ਦਿ  _______% per annum    _______% `
- **File:** `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.json`; **page:** 3; **class:** BAD; **proposed:** BAD; **expected script:** devanagari.
  **Metrics:** expected-script share `0.2807`; Latin letter share `0.7193`; private-use count `3`; `(cid:...)` count `0`; non-alphanumeric ratio `0.3813`; symbol ratio `0.0725`; letters `1621`; flags `{'pua': 3, 'cid': 0, 'replacement': 0, 'symbol_run': False}`.
  **PNG:** `data/processed/review_images/13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi_page_0003.png`
  **First 300 extracted characters (contact/ID patterns redacted):** `                               Page 3 of 29    Dual Rate (Fixed + Floating)/दोहरी दर (फिक्स्ड + फ्लोफ िंग)    Applicable Annualized Rate  of Interest  िागू िार्षिंक ब्याज दर  Fixed Rate of Interest during Fixed Rate Tenure followed by Floating  Rate of Interest during Floating Rate Tenure  नफक्स्ड र`
