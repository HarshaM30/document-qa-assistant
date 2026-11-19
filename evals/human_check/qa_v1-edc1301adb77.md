# Human check: faithfulness judge

Dataset `qa_v1@3a91ad46`, run `edc1301adb77`. 20 judged answers.

For each answer, read the passages and decide whether the judge's verdict is right:
*faithful* means every claim in the answer is supported by the passages (simple arithmetic allowed); *unfaithful* means at least one claim is not.

Mark exactly one box per answer by changing `[ ]` to `[x]`, then run `make eval-agreement`.

---

<!-- item: C06 judge: faithful -->
## 1. C06: Which had higher diluted earnings per share in 2025, JPMorgan Chase or Johnson & Johnson?

**Answer**

> JPMorgan Chase’s diluted earnings per share for 2025 were about $20 (net income applicable to common stockholders $55,681 million divided by 2,781.5 million diluted shares) [3], whereas Johnson & Johnson’s diluted earnings per share for 2025 were $11.03 [1][6].  
>
> Thus, JPMorgan Chase had the higher diluted EPS in 2025.

**Judge verdict: faithful.** The answer correctly identifies JPMorgan Chase's 2025 diluted EPS as approximately $20.05 (derived from $55,681 million / 2,781.5 million shares in passage [3]) and Johnson & Johnson's as $11.03 (from passages [1] and [6]), correctly concluding that JPMorgan Chase had the higher EPS.

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] ★ Johnson & Johnson 10-K FY2025 — Item 8. Financial statements and supplementary data (p. 85)**

> Table: The following is a reconciliation of basic net earnings per share to diluted net earnings per share for the fiscal years ended December 28, 2025, December 29, 2024 and December 31, 2023:
> Units: In Millions Except Per Share Amounts
> Basic net earnings per share from continuing operations | 2025: $11.13 | 2024: 5.84 | 2023: 5.26
> Basic net earnings per share from discontinued operations | 2025: — | 2024: — | 2023: 8.62
> Total net earnings per share - basic | 2025: 11.13 | 2024: 5.84 | 2023: 13.88
> Average shares outstanding — basic | 2025: 2,407.4 | 2024: 2,407.3 | 2023: 2,533.5
> Potential shares exercisable under stock option plans | 2025: 124.1 | 2024: 77.7 | 2023: 94.1
> Less: shares repurchased under treasury stock method | 2025: (102.1) | 2024: (55.6) | 2023: (67.2)
> Adjusted average shares outstanding — diluted | 2025: 2,429.4 | 2024: 2,429.4 | 2023: 2,560.4
> Diluted net earnings per share from continuing operations | 2025: 11.03 | 2024: 5.79 | 2023: 5.20
> Diluted net earnings per share from discontinuing operations | 2025: — | 2024: — | 2023: 8.52
> Total net earnings per share - diluted | 2025: $11.03 | 2024: 5.79 | 2023: 13.72
> (Shares in Millions) > The diluted net earnings per share calculation excluded the following number of shares related to stock options, as the exercise price of these options was greater than the average market value of the Company’s stock. | 2025: — | 2024: 54.1 | 2023: 43.0

**[2] Johnson & Johnson 10-K FY2024 — Item 8. Financial statements and supplementary data (p. 84)**

> Table: The following is a reconciliation of basic net earnings per share to diluted net earnings per share for the fiscal years ended December 29, 2024, December 31, 2023 and January 1, 2023:
> Units: In Millions Except Per Share Amounts
> Basic net earnings per share from continuing operations | 2024: $5.84 | 2023: 5.26 | 2022: 6.23
> Basic net earnings per share from discontinued operations | 2024: — | 2023: 8.62 | 2022: 0.60
> Total net earnings per share - basic | 2024: 5.84 | 2023: 13.88 | 2022: 6.83
> Average shares outstanding — basic | 2024: 2,407.3 | 2023: 2,533.5 | 2022: 2,625.2
> Potential shares exercisable under stock option plans | 2024: 77.7 | 2023: 94.1 | 2022: 140.1
> Less: shares repurchased under treasury stock method | 2024: (55.6) | 2023: (67.2) | 2022: (101.4)
> Adjusted average shares outstanding — diluted | 2024: 2,429.4 | 2023: 2,560.4 | 2022: 2,663.9
> Diluted net earnings per share from continuing operations | 2024: 5.79 | 2023: 5.20 | 2022: 6.14
> Diluted net earnings per share from discontinuing operations | 2024: — | 2023: 8.52 | 2022: 0.59
> Total net earnings per share - diluted | 2024: $5.79 | 2023: 13.72 | 2022: 6.73
> (Shares in Millions) > The diluted net earnings per share calculation excluded the following number of shares related to stock options, as the exercise price of these options was greater than the average market value of the Company’s stock. | 2024: 54.1 | 2023: 43.0 | 2022: 0.0

**[3] ★ JPMorgan Chase & Co. 10-K FY2025 — Item 8. Financial Statements and Supplementary Data (p. 288)**

> Table: The following table presents the calculation of net income applicable to common stockholders and basic and diluted EPS for the years ended December 31, 2025, 2024 and 2023.
> Units: in millions, except per share amounts
> Basic earnings per share > Net income | 2025: $57,048 | 2024: $58,471 | 2023: $49,552
> Basic earnings per share > Less: Preferred stock dividends | 2025: 1,099 | 2024: 1,259 | 2023: 1,501
> Basic earnings per share > Net income applicable to common equity | 2025: 55,949 | 2024: 57,212 | 2023: 48,051
> Basic earnings per share > Less: Dividends and undistributed earnings allocated to participating securities | 2025: 268 | 2024: 344 | 2023: 291
> Basic earnings per share > Net income applicable to common stockholders | 2025: $55,681 | 2024: $56,868 | 2023: $47,760
> Basic earnings per share > Total weighted-average basic shares outstanding | 2025: 2,776.5 | 2024: 2,873.9 | 2023: 2,938.6
> Net income per share | 2025: $20.05 | 2024: $19.79 | 2023: $16.25
> Diluted earnings per share > Net income applicable to common stockholders | 2025: $55,681 | 2024: $56,868 | 2023: $47,760
> Diluted earnings per share > Total weighted-average basic shares outstanding | 2025: 2,776.5 | 2024: 2,873.9 | 2023: 2,938.6
> Add: Dilutive impact of unvested PSUs, nondividend-earning RSUs and SARs | 2025: 5.0 | 2024: 5.1 | 2023: 4.5
> Total weighted-average diluted shares outstanding | 2025: 2,781.5 | 2024: 2,879.0 | 2023: 2,943.1

**[4] JPMorgan Chase & Co. 10-K FY2023 — Item 8. Financial Statements and Supplementary Data (p. 285)**

> Table: The following table presents the calculation of net income applicable to common stockholders and basic and diluted EPS for the years ended December 31, 2023, 2022 and 2021.
> Units: in millions, except per share amounts
> Basic earnings per share > Net income | 2023: $49,552 | 2022: $37,676 | 2021: $48,334
> Basic earnings per share > Less: Preferred stock dividends | 2023: 1,501 | 2022: 1,595 | 2021: 1,600
> Basic earnings per share > Net income applicable to common equity | 2023: 48,051 | 2022: 36,081 | 2021: 46,734
> Basic earnings per share > Less: Dividends and undistributed earnings allocated to participating securities | 2023: 291 | 2022: 189 | 2021: 231
> Basic earnings per share > Net income applicable to common stockholders | 2023: $47,760 | 2022: $35,892 | 2021: $46,503
> Basic earnings per share > Total weighted-average basic shares outstanding | 2023: 2,938.6 | 2022: 2,965.8 | 2021: 3,021.5
> Net income per share | 2023: $16.25 | 2022: $12.10 | 2021: $15.39
> Diluted earnings per share > Net income applicable to common stockholders | 2023: $47,760 | 2022: $35,892 | 2021: $46,503
> Diluted earnings per share > Total weighted-average basic shares outstanding | 2023: 2,938.6 | 2022: 2,965.8 | 2021: 3,021.5
> Add: Dilutive impact of unvested PSUs, nondividend-earning RSUs and SARs | 2023: 4.5 | 2022: 4.2 | 2021: 5.1
> Total weighted-average diluted shares outstanding | 2023: 2,943.1 | 2022: 2,970.0 | 2021: 3,026.6
> Net income per share | 2023: $16.23 | 2022: $12.09 | 2021: $15.36

**[5] JPMorgan Chase & Co. 10-K FY2024 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 56–57)**

> Firmwide overview
>
> JPMorganChase reported net income of $58.5 billion for 2024, up 18%, earnings per share of $19.75, ROE of 18% and ROTCE of 22%.
>
> •Total net revenue was $177.6 billion, up 12%, reflecting:
>
> –Net interest income (“NII”) of $92.6 billion, up 4%, driven by the impact of balance sheet actions, primarily reinvestments in the investment securities portfolio, higher revolving balances in Card Services, the timing impact of First Republic, higher wholesale deposit balances, and higher Markets net interest income, largely offset by deposit margin compression across the lines of business and lower average deposit balances in CCB. NII excluding Markets was $92.4 billion, up 3%.
>
> –Noninterest revenue (“NIR”) was $85.0 billion, up 23%, predominantly driven by a $7.9 billion net gain related to Visa shares recorded in the second quarter of 2024, higher asset management fees in AWM and CCB, higher investment banking fees, and lower net investment securities losses in Treasury and CIO.
>
> The prior year included the estimated bargain purchase gain of $2.8 billion associated with First Republic.
>
> •Noninterest expense was $91.8 billion, up 5%, driven by higher compensation expense, including higher revenue-related compensation and growth in the number of employees, as well as a $1.0 billion contribution of Visa shares to the JPMorgan Chase Foundation recorded in the second quarter of 2024, partially offset by lower FDIC-related expense, reflecting a $2.9 billion special assessment recognized in the fourth quarter of 2023, compared with a $725 million increase to the FDIC special assessment recognized in the first quarter of 2024.
>
> •The provision for credit losses was $10.7 billion, reflecting $8.6 billion of net charge-offs and a net addition to the allowance for credit losses of $2.0 billion. Net charge-offs increased by $2.4 billion, driven by Card Services, reflecting the seasoning of vintages originated in recent years, credit normalization, and balance growth.

**[6] ★ Johnson & Johnson 10-K FY2025 — Item 8. Financial statements and supplementary data (p. 49)**

> Table: Johnson & Johnson and subsidiaries consolidated statements of earnings (Dollars and Shares in Millions Except Per Share Amounts) (Note 1)
> Units: in Millions Except Per Share Amounts
> Net earnings per share (Notes 1 and 15) > Continuing operations - basic | 2025: $11.13 | 2024: 5.84 | 2023: 5.26
> Net earnings per share (Notes 1 and 15) > Discontinued operations - basic | 2025: — | 2024: — | 2023: 8.62
> Net earnings per share (Notes 1 and 15) > Total net earnings per share - basic | 2025: $11.13 | 2024: 5.84 | 2023: 13.88
> Continuing operations - diluted | 2025: $11.03 | 2024: 5.79 | 2023: 5.20
> Discontinued operations - diluted | 2025: — | 2024: — | 2023: 8.52
> Total net earnings per share - diluted | 2025: $11.03 | 2024: 5.79 | 2023: 13.72
> Average shares outstanding (Notes 1 and 15) > Basic | 2025: 2,407.4 | 2024: 2,407.3 | 2023: 2,533.5
> Average shares outstanding (Notes 1 and 15) > Diluted | 2025: 2,429.4 | 2024: 2,429.4 | 2023: 2,560.4

</details>

---

<!-- item: F03 judge: faithful -->
## 2. F03: How many people did Microsoft employ full-time as of June 30, 2026, and how many of them were in the U.S.?

**Answer**

> Microsoft employed approximately 223,000 people on a full‑time basis as of June 30, 2026, of which about 121,000 were in the United States[1].

**Judge verdict: faithful.** The answer correctly cites the total full-time employee count (223,000) and the U.S. employee count (121,000) as of June 30, 2026, which are explicitly stated in passage [1].

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] ★ Microsoft Corporation 10-K FY2026 — Item 1. Business (pp. 9–10)**

> Our Search advertising business competes with search engines, and a wide array of websites, social platforms, and portals that provide content and online offerings to end users.
>
> HUMAN CAPITAL RESOURCES
>
> As of June 30, 2026, we employed approximately 223,000 people on a full-time basis, 121,000 in the U.S. and 102,000 internationally. Of the total employees, 89,000 were in operations, including product support and consulting services, datacenter operations, and manufacturing and distribution; 77,000 were in product research and development; 43,000 were in sales and marketing; and 14,000 were in general and administration. Certain employees are subject to collective bargaining agreements.
>
> We design our programs to attract, reward, and retain top talent while fostering continuous employee development and reinforcing our organizational culture and values. Our total compensation offering is both highly differentiated and competitive within the market, and we also monitor pay equity across multiple dimensions. We have invested significantly in employee wellbeing and offer a differentiated benefits package which includes many physical, emotional, and financial wellness programs. We also provide access to continuous learning through a wide range of internal and external content, supporting professional growth across roles and disciplines. Through our employee listening systems, we gather direct feedback from our workforce, enabling us to adapt our programs and address employee needs globally with real-time insights. Additionally, our culture prioritizes the security of both our customers and Microsoft, embedding this responsibility across all teams and functions.
>
> OPERATIONS
>
> We have a global operations service center covering the Americas, Asia Pacific, Europe, and the Middle East that supports our business operations, including customer contract and order processing, billing, credit and collections, customer lifecycle AI and cloud operations, and vendor management and logistics.
>
> In addition to our operations center, we also operate datacenters throughout each of these regions. We continue to align our datacenter locations and server capacity to meet the evolving needs of our customers, particularly given the growing demand for AI services. Our datacenters depend on the availability of permitted and buildable land, predictable energy, networking supplies, and servers, including graphics processing units and other components.
>
> We engage third-party manufacturers to produce our devices and have implemented measures to enhance supply chain efficiency and resilience, including the ability to relocate production geographically.
>
> There are few qualified suppliers for certain components of our servers and devices.

**[2] Microsoft Corporation 10-K FY2024 — Item 1. Business (pp. 7–8)**

> As of June 2024, we’ve helped more than 2.5 million people in 92% of the world’s countries learn how to use AI.
>
> HUMAN CAPITAL RESOURCES
>
> Microsoft aims to recruit, develop, and retain world-changing talent from a diversity of backgrounds. To foster their and our success, we seek to create an environment where people can thrive and do their best work. We strive to maximize the potential of our human capital resources by creating a respectful, rewarding, and inclusive work environment that enables our global employees to create products and services that further our mission. Microsoft’s culture is grounded in growth mindset. This means everyone is on a continuous journey to learn and grow, operating as one company instead of multiple siloed businesses. Our culture also embeds the security of customers and Microsoft as a priority for every employee and across all of our organizations.
>
> As of June 30, 2024, we employed approximately 228,000 people on a full-time basis, 126,000 in the U.S. and 102,000 internationally. Of the total employed people, 86,000 were in operations, including product support and consulting services, datacenter operations, and manufacturing and distribution; 81,000 were in product research and development; 45,000 were in sales and marketing; and 16,000 were in general and administration. Certain employees are subject to collective bargaining agreements.
>
> We design our programs to attract, reward, and retain top talent, enable our employees’ continual growth, and reinforce our culture and values. Our total compensation opportunity is highly differentiated and market competitive. Our intended result is a global performance and development approach that fosters our culture, drives company performance, and competitive compensation that ensures equitable pay by role while supporting pay for performance.
>
> Diversity and inclusion are core to our business. As reported in our Global Diversity and Inclusion Reports, we monitor pay equity and career progress across multiple dimensions. We encourage every person at Microsoft to play an active role in creating an inclusive environment.
>
> We have invested significantly in employee wellbeing and offer a differentiated benefits package which includes many physical, emotional, and financial wellness programs. Our Occupational Health and Safety program helps to protect employees’ safety while they are working. We also have introduced Hybrid Workplace Flexibility guidance to better support leaders, managers, and employees in hybrid work scenarios.
>
> We believe providing employees with access to continual learning enables them to drive impact for the company.

**[3] Microsoft Corporation 10-K FY2025 — Item 1. Business (pp. 9–10)**

> We believe our gaming platform is effectively positioned against, and uniquely differentiated from, competitive products and services based on significant innovation in hardware architecture, user interface, developer tools, online gaming and entertainment services, and continued strong content from our own first-party game franchises as well as other digital content offerings.
>
> Our Search and news advertising business competes with search engines, and a wide array of websites, social platforms, and portals that provide content and online offerings to end users.
>
> HUMAN CAPITAL RESOURCES
>
> As of June 30, 2025, we employed approximately 228,000 people on a full-time basis, 125,000 in the U.S. and 103,000 internationally. Of the total employees, 89,000 were in operations, including product support and consulting services, datacenter operations, and manufacturing and distribution; 80,000 were in product research and development; 44,000 were in sales and marketing; and 15,000 were in general and administration. Certain employees are subject to collective bargaining agreements.
>
> We design our programs to attract, reward, and retain top talent while fostering continuous employee development and reinforcing our organizational culture and values. Our total compensation offering is both highly differentiated and competitive within the market, and we also monitor pay equity across multiple dimensions. We have invested significantly in employee wellbeing and offer a differentiated benefits package which includes many physical, emotional, and financial wellness programs. We also provide access to continuous learning through a wide range of internal and external content, supporting professional growth across roles and disciplines. Through our employee listening systems, we gather direct feedback from our workforce, enabling us to adapt our programs and address employee needs globally with real-time insights. Additionally, our culture prioritizes the security of both our customers and Microsoft, embedding this responsibility across all teams and functions.
>
> OPERATIONS
>
> We have regional operations service centers in the Americas, Asia Pacific, Europe, and the Middle East that support our business operations, including customer contract and order processing, billing, credit and collections, customer lifecycle AI and cloud operations, and vendor management and logistics.
>
> In addition to our operations centers, we also operate datacenters throughout each of these regions. We continue to align our datacenter locations and server capacity to meet the evolving needs of our customers, particularly given the growing demand for AI services.

**[4] Microsoft Corporation 10-K FY2024 — Item 1. Business (p. 7)**

> We also continue to make progress toward our overall commitment to double the number of Black and African American and Hispanic and Latinx leaders in the U.S. by 2025.
>
> Investing in Digital Skills
>
> Microsoft’s Skills for Jobs initiative aims to support a more skills-based labor market, with greater flexibility and accessible learning paths to develop the right skills needed for the most in-demand jobs. This initiative brings together classes, Career Essentials Certificates, and other resources from LinkedIn, GitHub, and Microsoft Learn, and is built on data insights drawn from LinkedIn’s Economic Graph. Our goal was to train and certify 10 million learners by 2025. As of May 2024, we have surpassed that goal, training and certifying 12.6 million learners. We also launched a campaign in the United States in 2021 to help skill and recruit 250,000 people into the nation’s cybersecurity workforce by 2025, representing half of the country’s workforce shortage. To that end, we are making curriculum available free of charge to all of the nation’s higher education institutions, providing training for new and existing faculty, and providing scholarships and supplemental resources to 25,000 students. The cyber skills initiative has expanded to 27 additional countries that show elevated cyberthreat risks coupled with significant gaps in their cybersecurity workforces, where we’ve partnered with nonprofits and other educational institutions to train the next generation of cybersecurity workers.
>
> Generative AI is creating unparalleled opportunities to empower workers globally, but only if everyone has the skills to use it. In June 2023, we launched an AI Skills initiative to help everyone learn how to harness the power of AI. This includes a new LinkedIn learning pathway offering new coursework on learning the foundations of generative AI. We also launched a new global grant challenge to uncover new ways of training workers on generative AI and provide greater access to digital learning events and resources. Additionally, we extended our reach in rural communities, including through our TechSpark initiative in the United States. As of June 2024, we’ve helped more than 2.5 million people in 92% of the world’s countries learn how to use AI.
>
> HUMAN CAPITAL RESOURCES
>
> Microsoft aims to recruit, develop, and retain world-changing talent from a diversity of backgrounds.

**[5] Microsoft Corporation 10-K FY2024 — Item 8. Financial Statements And Supplementary Data (pp. 90–91)**

> As of June 30, 2024, 68 million shares of our common stock were reserved for future issuance through the ESPP.
>
> Savings Plans
>
> We have savings plans in the U.S. that qualify under Section 401(k) of the Internal Revenue Code, and a number of savings plans in international locations. Eligible U.S. employees may contribute a portion of their salary into the savings plans, subject to certain limitations. We match a portion of each dollar a participant contributes into the plans. Employer-funded retirement benefits for all plans were $1.7 billion, $1.6 billion, and $1.4 billion in fiscal years 2024, 2023, and 2022, respectively, and were expensed as contributed.
>
> NOTE 19 — SEGMENT INFORMATION AND GEOGRAPHIC DATA
>
> In its operation of the business, management, including our chief operating decision maker, who is also our Chief Executive Officer, reviews certain financial information, including segmented internal profit and loss statements prepared on a basis not consistent with GAAP. During the periods presented, we reported our financial performance based on the following segments: Productivity and Business Processes, Intelligent Cloud, and More Personal Computing.
>
> Our reportable segments are described below.
>
> Productivity and Business Processes
>
> Our Productivity and Business Processes segment consists of products and services in our portfolio of productivity, communication, and information services, spanning a variety of devices and platforms. This segment primarily comprises:
>
> Office Commercial (Office 365 subscriptions, the Office 365 portion of Microsoft 365 Commercial subscriptions, and Office licensed on-premises), comprising Office, Exchange, SharePoint, Microsoft Teams, Office 365 Security and Compliance, Microsoft Viva, and Copilot for Microsoft 365.
>
> Office Consumer, including Microsoft 365 Consumer and Copilot Pro subscriptions, Office licensed on-premises, and other Office services.
>
> LinkedIn, including Talent Solutions, Marketing Solutions, Premium Subscriptions, and Sales Solutions.
>
> Dynamics business solutions, including Dynamics 365, comprising a set of intelligent, cloud-based applications across ERP, CRM, Power Apps, and Power Automate; and on-premises ERP and CRM applications.
>
> Intelligent Cloud
>
> Our Intelligent Cloud segment consists of our public, private, and hybrid server products and cloud services that can power modern business and developers. This segment primarily comprises:

**[6] Microsoft Corporation 10-K FY2026 — Item 7. Management’s Discussion And Analysis Of Financial Condition And Results Of Operations (p. 44)**

> Table: The following table outlines the expected future recognition of unearned revenue as of June 30, 2026:
> Units: In millions
> Three Months Ending > September 30, 2026 | $28,589
> Three Months Ending > December 31, 2026 | 22,556
> Three Months Ending > March 31, 2027 | 15,457
> Three Months Ending > June 30, 2027 | 6,363
> Three Months Ending > Thereafter | 2,747
> Three Months Ending > Total | $75,712

</details>

---

<!-- item: F04 judge: faithful -->
## 3. F04: What are Microsoft's reportable segments in its fiscal 2026 10-K?

**Answer**

> Microsoft’s reportable segments are Productivity and Business Processes, Intelligent Cloud, and More Personal Computing[1†L4-L7][2†L9-L12].

**Judge verdict: faithful.** The answer correctly lists the three reportable segments (Productivity and Business Processes, Intelligent Cloud, and More Personal Computing) as stated in passages [1] and [2], which describe the segment structure applicable to the fiscal years discussed.

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] ★ Microsoft Corporation 10-K FY2025 — Item 7. Management’s Discussion And Analysis Of Financial Condition And Results Of Operations (pp. 36–37)**

> Seasonality
>
> Our revenue fluctuates quarterly and is generally higher in the fourth quarter of our fiscal year. Fourth quarter revenue is driven by a higher volume of multi-year contracts executed during the period.
>
> Reportable Segments
>
> We report our financial performance based on the following segments: Productivity and Business Processes, Intelligent Cloud, and More Personal Computing. The segment amounts included in MD&A are presented on a basis consistent with our internal management reporting.
>
> In August 2024, we announced changes to the composition of our segments. These changes align our segments with how we currently manage our business, most notably bringing the commercial components of Microsoft 365 together in the Productivity and Business Processes segment. Beginning in fiscal year 2025, the information that our chief operating decision maker is regularly provided and reviews for purposes of allocating resources and assessing performance reflects these segment changes. Prior period segment information has been recast to conform to the way we internally manage and monitor our business during fiscal year 2025.
>
> Additional information on our reportable segments is contained in Note 18 – Segment Information and Geographic Data of the Notes to Financial Statements (Part II, Item 8 of this Form 10-K).
>
> Metrics
>
> We use metrics in assessing the performance of our business and to make informed decisions regarding the allocation of resources. We disclose metrics to enable investors to evaluate progress against our ambitions, provide transparency into performance trends, and reflect the continued evolution of our products and services. Our commercial and other business metrics are fundamentally connected based on how customers use our products and services. The metrics are disclosed in the MD&A or the Notes to Financial Statements (Part II, Item 8 of this Form 10-K). Financial metrics are calculated based on financial results prepared in accordance with accounting principles generally accepted in the United States of America (“GAAP”), and growth comparisons relate to the corresponding period of last fiscal year.
>
> In the first quarter of fiscal year 2025, we made updates to our metrics in connection with the segment changes described above. These changes align our metrics with how we manage and monitor certain businesses. The key change was bringing the commercial components of Microsoft 365 together and creating a new Microsoft 365 Commercial cloud revenue growth metric.

**[2] ★ Microsoft Corporation 10-K FY2025 — Item 1. Business (pp. 4–5)**

> Tackling security from all angles with our integrated, end-to-end solutions spanning security, compliance, identity, and management, across all clouds and platforms.
>
> Our future growth depends on our ability to transcend current product category definitions, business models, and sales motions.
>
> Commitment to Sustainability
>
> Microsoft is committed to sustainability and our approach to addressing climate change starts with the sustainability of our own business. In 2020, we announced goals to become a carbon negative, water positive, and zero waste company by 2030. Since announcing these goals, we have made meaningful progress while having seen major changes in both the technology sector and in our understanding of what it will take to meet our goals. Progress toward these goals can be found in our annual Environmental Sustainability Report.
>
> OPERATING SEGMENTS
>
> We operate our business and report our financial performance using three segments: Productivity and Business Processes, Intelligent Cloud, and More Personal Computing. Our segments provide management with a comprehensive financial view of our key businesses. The segments enable the alignment of strategies and objectives across the development, sales, marketing, and services organizations, and they provide a framework for timely and rational allocation of resources within businesses.
>
> In August 2024, we announced changes to the composition of our segments. These changes align our segments with how we currently manage our business, most notably bringing the commercial components of Microsoft 365 together in the Productivity and Business Processes segment. Beginning in fiscal year 2025, the information that our chief operating decision maker is regularly provided and reviews for purposes of allocating resources and assessing performance reflects these segment changes.
>
> Additional information on our operating segments and geographic and product information is contained in Note 18 – Segment Information and Geographic Data of the Notes to Financial Statements (Part II, Item 8 of this Form 10-K).
>
> Our reportable segments are described below.
>
> Productivity and Business Processes
>
> Our Productivity and Business Processes segment consists of products and services in our portfolio of productivity, communication, and information services, spanning a variety of devices and platforms. This segment primarily comprises:
>
> Microsoft 365 Commercial products and cloud services, including Microsoft 365 Commercial cloud, comprising Microsoft 365 Commercial, Enterprise Mobility + Security, the cloud portion of Windows Commercial, the per-user portion of Power BI, Exchange, SharePoint, Microsoft Teams, Microsoft 365 Security and Compliance, and Microsoft 365 Copilot; and Microsoft 365 Commercial products, comprising Windows Commercial on-premises and Office licensed on-premises.

**[3] Microsoft Corporation 10-K FY2026 — Item 8. Financial Statements And Supplementary Data (p. 84)**

> Table: Segment revenue, cost of revenue, operating expenses, and operating income were as follows during the periods presented:
> Units: In millions
> Total > Operating expenses | 2026: 70,228 | 2025: 65,365 | 2024: 61,575
> Total > Operating income | 2026: $155,237 | 2025: $128,528 | 2024: $109,433

**[4] Microsoft Corporation 10-K FY2026 — Item 8. Financial Statements And Supplementary Data (p. 77)**

> Table: Unearned revenue by segment was as follows:
> Units: In millions
> (In millions) > Productivity and Business Processes | 2026: $57,936 | 2025: $50,567
> (In millions) > Intelligent Cloud | 2026: 14,942 | 2025: 14,022
> (In millions) > More Personal Computing | 2026: 2,834 | 2025: 2,676
> (In millions) > Total | 2026: $75,712 | 2025: $67,265

**[5] Microsoft Corporation 10-K FY2025 — Item 8. Financial Statements And Supplementary Data (p. 84)**

> Table: Segment revenue, cost of revenue, operating expenses, and operating income were as follows during the periods presented:
> Units: In millions
> Total > Operating Income | 2025: $128,528 | 2024: $109,433 | 2023: $88,523

**[6] Microsoft Corporation 10-K FY2025 — Item 8. Financial Statements And Supplementary Data (p. 76)**

> Table: Unearned revenue by segment was as follows:
> Units: In millions
> (In millions) > Productivity and Business Processes | 2025: $50,567 | 2024: $43,599
> (In millions) > Intelligent Cloud | 2025: 14,022 | 2024: 13,683
> (In millions) > More Personal Computing | 2025: 2,676 | 2024: 2,902
> (In millions) > Total | 2025: $67,265 | 2024: $60,184

</details>

---

<!-- item: F05 judge: faithful -->
## 4. F05: Into which segments does Amazon organize its operations?

**Answer**

> Amazon organizes its operations into three reportable segments: **North America, International, and Amazon Web Services (AWS)**[1†L9-L13][3†L9-L13]

**Judge verdict: faithful.** The answer correctly identifies the three segments (North America, International, and AWS) as stated in multiple passages, including [1], [3], [4], and [5].

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] ★ Amazon.com, Inc. 10-K FY2023 — Item 8. Financial Statements and Supplementary Data (pp. 67–68)**

> These assessments or settlements could result in changes to our contingencies related to positions on prior years’ tax filings. The actual amount of any change could vary significantly depending on the ultimate timing and nature of any settlements. We cannot currently provide an estimate of the range of possible outcomes.
>
> Note 10 — SEGMENT INFORMATION
>
> We have organized our operations into three segments: North America, International, and AWS. We allocate to segment results the operating expenses “Fulfillment,” “Technology and infrastructure,” “Sales and marketing,” and “General and administrative” based on usage, which is generally reflected in the segment in which the costs are incurred. The majority of technology costs recorded in “Technology and infrastructure” are incurred in the U.S. and are included in our North America and AWS segments. The majority of infrastructure costs recorded in “Technology and infrastructure” are allocated to the AWS segment based on usage. There are no internal revenue transactions between our reportable segments. Our chief operating decision maker (“CODM”) regularly reviews consolidated net sales, consolidated operating expenses, and consolidated operating income (loss) by segment. Amounts included in consolidated operating expenses include “Cost of sales,” “Fulfillment,” “Technology and infrastructure,” “Sales and marketing,” “General and administrative,” and “Other operating expense (income), net.” Our CODM manages our business by reviewing annual forecasts and consolidated results by segment on a quarterly basis.
>
> North America
>
> The North America segment primarily consists of amounts earned from retail sales of consumer products (including from sellers) and advertising and subscription services through North America-focused online and physical stores. This segment includes export sales from these online stores.
>
> International
>
> The International segment primarily consists of amounts earned from retail sales of consumer products (including from sellers) and advertising and subscription services through internationally-focused online stores. This segment includes export sales from these internationally-focused online stores (including export sales from these online stores to customers in the U.S., Mexico, and Canada), but excludes export sales from our North America-focused online stores.
>
> AWS
>
> The AWS segment consists of amounts earned from global sales of compute, storage, database, and other services for start-ups, enterprises, government agencies, and academic institutions.
>
> Information on reportable segments and reconciliation to consolidated net income (loss) is as follows (in millions):

**[2] Amazon.com, Inc. 10-K FY2025 — Item 8. Financial Statements and Supplementary Data (pp. 67–68)**

> If this matter is adversely resolved, we could recognize significant additional tax expense, including for taxes previously paid.
>
> Changes in tax laws, regulations, administrative practices, principles, and interpretations may impact our tax contingencies. Due to various factors, including the inherent complexities and uncertainties of the judicial, administrative, and regulatory processes in certain jurisdictions, the timing of the resolution of income tax controversies is highly uncertain, and the amounts ultimately paid, if any, upon resolution of the issues raised by the taxing authorities may differ from the amounts accrued.
>
> Note 10 — SEGMENT INFORMATION
>
> We have organized our operations into three segments: North America, International, and AWS. We allocate to segment results the operating expenses “Fulfillment,” “Technology and infrastructure,” “Sales and marketing,” and “General and administrative” based on usage, which is generally reflected in the segment in which the costs are incurred. The majority of technology costs recorded in “Technology and infrastructure” are incurred in the U.S. and are included in our North America and AWS segments. The majority of infrastructure costs recorded in “Technology and infrastructure” are allocated to the AWS segment based on usage. There are no internal revenue transactions between our reportable segments. Our chief operating decision maker (“CODM”) is our President and Chief Executive Officer. Our CODM regularly reviews consolidated net sales, consolidated operating expenses, and consolidated operating income (loss) by segment. Amounts included in consolidated operating expenses include “Cost of sales,” “Fulfillment,” “Technology and infrastructure,” “Sales and marketing,” “General and administrative,” and “Other operating expense (income), net.” Our CODM manages our business primarily by reviewing consolidated results by segment on a quarterly basis, and using those results along with forecasts and other non-financial information in our annual budgeting process.
>
> North America
>
> The North America segment primarily consists of amounts earned from retail sales of consumer products (including from sellers) and advertising and subscription services through North America-focused online and physical stores. This segment includes export sales from these online stores.
>
> International
>
> The International segment primarily consists of amounts earned from retail sales of consumer products (including from sellers) and advertising and subscription services through internationally-focused online stores.

**[3] ★ Amazon.com, Inc. 10-K FY2024 — Item 1. Business (p. 3)**

> This Annual Report on Form 10-K and the documents incorporated herein by reference contain forward-looking statements based on expectations, estimates, and projections as of the date of this filing. Actual results and outcomes may differ materially from those expressed in forward-looking statements. See Item 1A of Part I — “Risk Factors.” As used herein, “Amazon.com,” “we,” “our,” and similar terms include Amazon.com, Inc. and its subsidiaries, unless the context indicates otherwise.
>
> General
>
> We seek to be Earth’s most customer-centric company. We are guided by four principles: customer obsession rather than competitor focus, passion for invention, commitment to operational excellence, and long-term thinking. In each of our segments, we serve our primary customer sets, consisting of consumers, sellers, developers, enterprises, content creators, advertisers, and employees.
>
> We have organized our operations into three segments: North America, International, and Amazon Web Services (“AWS”). These segments reflect the way the Company evaluates its business performance and manages its operations. Information on our net sales is contained in Item 8 of Part II, “Financial Statements and Supplementary Data — Note 10 — Segment Information.”
>
> Consumers
>
> We serve consumers through our online and physical stores and focus on selection, price, and convenience. We design our stores to enable hundreds of millions of unique products to be sold by us and by third parties across dozens of product categories. Customers access our offerings through our websites, mobile apps, Alexa, devices, streaming, and physically visiting our stores. We also manufacture and sell electronic devices, including Kindle, Fire tablet, Fire TV, Echo, Ring, Blink, and eero, and we develop and produce media content. We seek to offer our customers low prices, fast and free delivery, easy-to-use functionality, and timely customer service. In addition, we offer subscription services such as Amazon Prime, a membership program that includes fast, free shipping on tens of millions of items, access to award-winning movies and series, live sports, and other benefits.
>
> We fulfill customer orders in a number of ways, including through: North America and International fulfillment networks that we operate; co-sourced and outsourced arrangements in certain countries; digital delivery; and through our physical stores. We operate customer service centers globally, which are supplemented by co-sourced arrangements.

**[4] Amazon.com, Inc. 10-K FY2025 — Item 1. Business (p. 3)**

> This Annual Report on Form 10-K and the documents incorporated herein by reference contain forward-looking statements based on expectations, estimates, and projections as of the date of this filing. Actual results and outcomes may differ materially from those expressed in forward-looking statements. See Item 1A of Part I — “Risk Factors.” As used herein, “Amazon.com,” “we,” “our,” and similar terms include Amazon.com, Inc. and its subsidiaries, unless the context indicates otherwise.
>
> General
>
> We seek to be Earth’s most customer-centric company. We are guided by four principles: customer obsession rather than competitor focus, passion for invention, commitment to operational excellence, and long-term thinking. In each of our segments, we serve our primary customer sets, consisting of consumers, sellers, developers, enterprises, content creators, advertisers, and employees.
>
> We have organized our operations into three segments: North America, International, and Amazon Web Services (“AWS”). These segments reflect the way the Company evaluates its business performance and manages its operations. Information on our net sales is contained in Item 8 of Part II, “Financial Statements and Supplementary Data — Note 10 — Segment Information.”
>
> Consumers
>
> We serve consumers through our online and physical stores and focus on selection, price, and convenience. We design our stores to enable hundreds of millions of unique products to be sold by us and by third parties across dozens of product categories. Customers access our offerings through our websites, mobile apps, Alexa, devices, streaming, and physically visiting our stores. We also manufacture and sell electronic devices, including Kindle, Fire tablet, Fire TV, Echo, Ring, Blink, and eero, and we develop and produce media content. We seek to offer our customers low prices, fast and free delivery, easy-to-use functionality, and timely customer service. In addition, we offer subscription services such as Amazon Prime, a membership program that includes fast, free shipping on tens of millions of items, access to award-winning movies and series, live sports, and other benefits.
>
> We fulfill customer orders in a number of ways, including through: North America and International fulfillment networks that we operate; co-sourced and outsourced arrangements in certain countries; digital delivery; and through our physical stores. We operate customer service centers globally, which are supplemented by co-sourced arrangements.

**[5] Amazon.com, Inc. 10-K FY2023 — Item 1. Business (p. 3)**

> This Annual Report on Form 10-K and the documents incorporated herein by reference contain forward-looking statements based on expectations, estimates, and projections as of the date of this filing. Actual results and outcomes may differ materially from those expressed in forward-looking statements. See Item 1A of Part I — “Risk Factors.” As used herein, “Amazon.com,” “we,” “our,” and similar terms include Amazon.com, Inc. and its subsidiaries, unless the context indicates otherwise.
>
> General
>
> We seek to be Earth’s most customer-centric company. We are guided by four principles: customer obsession rather than competitor focus, passion for invention, commitment to operational excellence, and long-term thinking. In each of our segments, we serve our primary customer sets, consisting of consumers, sellers, developers, enterprises, content creators, advertisers, and employees.
>
> We have organized our operations into three segments: North America, International, and Amazon Web Services (“AWS”). These segments reflect the way the Company evaluates its business performance and manages its operations. Information on our net sales is contained in Item 8 of Part II, “Financial Statements and Supplementary Data — Note 10 — Segment Information.”
>
> Consumers
>
> We serve consumers through our online and physical stores and focus on selection, price, and convenience. We design our stores to enable hundreds of millions of unique products to be sold by us and by third parties across dozens of product categories. Customers access our offerings through our websites, mobile apps, Alexa, devices, streaming, and physically visiting our stores. We also manufacture and sell electronic devices, including Kindle, Fire tablet, Fire TV, Echo, Ring, Blink, and eero, and we develop and produce media content. We seek to offer our customers low prices, fast and free delivery, easy-to-use functionality, and timely customer service. In addition, we offer subscription services such as Amazon Prime, a membership program that includes fast, free shipping on tens of millions of items, access to award-winning movies and series, and other benefits.
>
> We fulfill customer orders in a number of ways, including through: North America and International fulfillment networks that we operate; co-sourced and outsourced arrangements in certain countries; digital delivery; and through our physical stores. We operate customer service centers globally, which are supplemented by co-sourced arrangements.

**[6] Amazon.com, Inc. 10-K FY2024 — Item 8. Financial Statements and Supplementary Data (p. 68)**

> (1)North America and International segment assets primarily consist of property and equipment, operating leases, inventory, accounts receivable, and digital video and music content.
>
> (2)AWS segment assets primarily consist of property and equipment, accounts receivable, and operating leases.
>
> Property and equipment, net by segment is as follows (in millions):

</details>

---

<!-- item: F06 judge: faithful -->
## 5. F06: How many full-time and part-time employees did Amazon have at the end of 2023?

**Answer**

> Amazon employed approximately 1,525,000 full‑time and part‑time employees as of December 31, 2023[5].

**Judge verdict: faithful.** The answer correctly cites the number of employees (1,525,000) and the date (December 31, 2023) as stated in passage [5].

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] Amazon.com, Inc. 10-K FY2025 — Item 1. Business (p. 4)**

> They may secure better terms from suppliers, adopt more aggressive pricing, pursue restrictive distribution agreements that restrict our access to supply, direct consumers to their own offerings instead of ours, lock-in potential customers with restrictive terms, and devote more resources to technology, infrastructure, fulfillment, and marketing. The internet and other technologies including artificial intelligence facilitate competitive entry and comparison shopping, which enhances the ability of new, smaller, or lesser-known businesses to compete against us. Each of our businesses is also subject to rapid change and the development of new business models and the entry of new and well-funded competitors. Other companies also may enter into business combinations or alliances that strengthen their competitive positions.
>
> Intellectual Property
>
> We regard our trademarks, service marks, copyrights, patents, domain names, trade dress, trade secrets, proprietary technologies, and similar intellectual property as critical to our success, and we rely on trademark, copyright, and patent law, trade-secret protection, and confidentiality and/or license agreements with our employees, customers, partners, and others to protect our proprietary rights. We have registered, or applied for the registration of, a number of U.S. and international domain names, trademarks, service marks, and copyrights. Additionally, we have filed U.S. and international patent applications covering certain of our proprietary technology.
>
> Seasonality
>
> Our business is affected by seasonality, which historically has resulted in higher sales volume during our fourth quarter, which ends December 31.
>
> Human Capital
>
> Our employees are critical to our mission of being Earth’s most customer-centric company. As of December 31, 2025, we employed approximately 1,576,000 full-time and part-time employees. Additionally, we use independent contractors and temporary personnel to supplement our workforce. Competition for qualified personnel is intense, particularly for software engineers, computer scientists, and other technical staff (including for artificial intelligence and machine learning technologies), and constrained labor markets have increased competition for personnel across other parts of our business.
>
> We strive to be Earth’s best employer. We rely on numerous and evolving initiatives to implement this objective and invent mechanisms for talent development, including competitive pay and benefits, flexible work arrangements, and skills training and educational programs such as Amazon Career Choice (education funding for eligible employees). Over 300,000 Amazon employees around the world have participated in Career Choice.

**[2] Amazon.com, Inc. 10-K FY2024 — Item 1. Business (p. 4)**

> They may secure better terms from suppliers, adopt more aggressive pricing, pursue restrictive distribution agreements that restrict our access to supply, direct consumers to their own offerings instead of ours, lock-in potential customers with restrictive terms, and devote more resources to technology, infrastructure, fulfillment, and marketing. The internet facilitates competitive entry and comparison shopping, which enhances the ability of new, smaller, or lesser-known businesses to compete against us. Each of our businesses is also subject to rapid change and the development of new business models and the entry of new and well-funded competitors. Other companies also may enter into business combinations or alliances that strengthen their competitive positions.
>
> Intellectual Property
>
> We regard our trademarks, service marks, copyrights, patents, domain names, trade dress, trade secrets, proprietary technologies, and similar intellectual property as critical to our success, and we rely on trademark, copyright, and patent law, trade-secret protection, and confidentiality and/or license agreements with our employees, customers, partners, and others to protect our proprietary rights. We have registered, or applied for the registration of, a number of U.S. and international domain names, trademarks, service marks, and copyrights. Additionally, we have filed U.S. and international patent applications covering certain of our proprietary technology.
>
> Seasonality
>
> Our business is affected by seasonality, which historically has resulted in higher sales volume during our fourth quarter, which ends December 31.
>
> Human Capital
>
> Our employees are critical to our mission of being Earth’s most customer-centric company. As of December 31, 2024, we employed approximately 1,556,000 full-time and part-time employees. Additionally, we use independent contractors and temporary personnel to supplement our workforce. Competition for qualified personnel is intense, particularly for software engineers, computer scientists, and other technical staff, and constrained labor markets have increased competition for personnel across other parts of our business.
>
> We strive to be Earth’s best employer. We rely on numerous and evolving initiatives to implement this objective and invent mechanisms for talent development, including competitive pay and benefits, flexible work arrangements, and skills training and educational programs such as Amazon Career Choice (education funding for eligible employees). Over 240,000 Amazon employees around the world have participated in Career Choice. We also continue to inspect and refine the mechanisms we use to hire, develop, evaluate, and retain our employees.

**[3] Johnson & Johnson 10-K FY2023 — Item 1. Business (p. 11)**

> Table: As of December 31, 2023, the number of employees was approximately:
> Employees1 | 2023: 134,400
> Full-time equivalent (FTE) positions2 | 2023: 131,900

**[4] Johnson & Johnson 10-K FY2024 — Item 1. Business (p. 11)**

> Table: As of December 29, 2024 and December 31, 2023 the number of employees was approximately:
> Employees(1) | 2024: 139,800 | 2023: 134,400
> Full-time equivalent (FTE) positions(2) | 2024: 138,100 | 2023: 131,900

**[5] ★ Amazon.com, Inc. 10-K FY2023 — Item 1. Business (p. 4)**

> The internet facilitates competitive entry and comparison shopping, which enhances the ability of new, smaller, or lesser-known businesses to compete against us. Each of our businesses is also subject to rapid change and the development of new business models and the entry of new and well-funded competitors. Other companies also may enter into business combinations or alliances that strengthen their competitive positions.
>
> Intellectual Property
>
> We regard our trademarks, service marks, copyrights, patents, domain names, trade dress, trade secrets, proprietary technologies, and similar intellectual property as critical to our success, and we rely on trademark, copyright, and patent law, trade-secret protection, and confidentiality and/or license agreements with our employees, customers, partners, and others to protect our proprietary rights. We have registered, or applied for the registration of, a number of U.S. and international domain names, trademarks, service marks, and copyrights. Additionally, we have filed U.S. and international patent applications covering certain of our proprietary technology.
>
> Seasonality
>
> Our business is affected by seasonality, which historically has resulted in higher sales volume during our fourth quarter, which ends December 31.
>
> Human Capital
>
> Our employees are critical to our mission of being Earth’s most customer-centric company. As of December 31, 2023, we employed approximately 1,525,000 full-time and part-time employees. Additionally, we use independent contractors and temporary personnel to supplement our workforce. Competition for qualified personnel is intense, particularly for software engineers, computer scientists, and other technical staff, and constrained labor markets have increased competition for personnel across other parts of our business.
>
> As we strive to be Earth’s best employer, we focus on investment and innovation, inclusion and diversity, safety, and engagement to hire and develop the best talent. We rely on numerous and evolving initiatives to implement these objectives and invent mechanisms for talent development, including competitive pay and benefits, flexible work arrangements, and skills training and educational programs such as Amazon Career Choice (education funding for eligible employees) and the Amazon Technical Academy (software development engineer training). Over 175,000 Amazon employees around the world have participated in Career Choice. We also continue to inspect and refine the mechanisms we use to hire, develop, evaluate, and retain our employees to promote equity for all candidates and employees.

**[6] Amazon.com, Inc. 10-K FY2025 — Item 8. Financial Statements and Supplementary Data (p. 37)**

> Table: (in millions, except per share data)
> Units: in millions, except per share data
> Net product sales | Year Ended December 31, 2023: $255,887 | Year Ended December 31, 2024: $272,311 | Year Ended December 31, 2025: $296,266
> Net service sales | Year Ended December 31, 2023: 318,898 | Year Ended December 31, 2024: 365,648 | Year Ended December 31, 2025: 420,658
> Total net sales | Year Ended December 31, 2023: 574,785 | Year Ended December 31, 2024: 637,959 | Year Ended December 31, 2025: 716,924
> Operating expenses > Cost of sales | Year Ended December 31, 2023: 304,739 | Year Ended December 31, 2024: 326,288 | Year Ended December 31, 2025: 356,414
> Operating expenses > Fulfillment | Year Ended December 31, 2023: 90,619 | Year Ended December 31, 2024: 98,505 | Year Ended December 31, 2025: 109,074
> Operating expenses > Technology and infrastructure | Year Ended December 31, 2023: 85,622 | Year Ended December 31, 2024: 88,544 | Year Ended December 31, 2025: 108,521
> Operating expenses > Sales and marketing | Year Ended December 31, 2023: 44,370 | Year Ended December 31, 2024: 43,907 | Year Ended December 31, 2025: 47,129
> Operating expenses > General and administrative | Year Ended December 31, 2023: 11,816 | Year Ended December 31, 2024: 11,359 | Year Ended December 31, 2025: 11,172
> Operating expenses > Other operating expense (income), net | Year Ended December 31, 2023: 767 | Year Ended December 31, 2024: 763 | Year Ended December 31, 2025: 4,639
> Operating expenses > Total operating expenses | Year Ended December 31, 2023: 537,933 | Year Ended December 31, 2024: 569,366 | Year Ended December 31, 2025: 636,949

</details>

---

<!-- item: F07 judge: faithful -->
## 6. F07: How many employees did JPMorgan Chase have at the end of 2025, and in how many countries?

**Answer**

> JPMorgan Chase had **318,512 employees** worldwide at the end of 2025, and its workforce was located in **66 countries**[1].

**Judge verdict: faithful.** The answer correctly cites the total number of employees (318,512) and the number of countries (66) from passage [1], which corresponds to the data as of December 31, 2025.

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] ★ JPMorgan Chase & Co. 10-K FY2025 — Item 1. Business (p. 9)**

> Table: As of December 31, 2025, JPMorganChase had 318,512 employees globally. JPMorganChase’s employees are located in 66 countries, with 58% of the Firm’s employees located in the U.S. The following table presents the distribution of the Firm’s global work
> North America | Employees: 185,208 | Employee Breakdown by LOB and Corporate LOB: CCB | Employee Breakdown by LOB and Corporate Employees: 144,196
> Asia-Pacific | Employees: 96,499 | Employee Breakdown by LOB and Corporate LOB: CIB | Employee Breakdown by LOB and Corporate Employees: 94,563
> Europe/Middle East/Africa | Employees: 31,030 | Employee Breakdown by LOB and Corporate LOB: AWM | Employee Breakdown by LOB and Corporate Employees: 29,722
> Latin America/Caribbean | Employees: 5,775 | Employee Breakdown by LOB and Corporate LOB: Corporate | Employee Breakdown by LOB and Corporate Employees: 50,031
> Total Firm | Employees: 318,512 | Employee Breakdown by LOB and Corporate LOB: Total Firm | Employee Breakdown by LOB and Corporate Employees: 318,512

**[2] JPMorgan Chase & Co. 10-K FY2023 — Item 1. Business (p. 4)**

> Table: As of December 31, 2023, JPMorgan Chase had 309,926 employees globally, an increase of 16,203 employees from the prior year. The increase was primarily attributable to growth in front office, operations and technology, as well as the impact of the Fi
> North America | Employees: 186,751 | Employee Breakdown by LOB and Corporate LOB: CCB | Employee Breakdown by LOB and Corporate Employees: 141,640
> Asia-Pacific | Employees: 88,406 | Employee Breakdown by LOB and Corporate LOB: CIB | Employee Breakdown by LOB and Corporate Employees: 74,404
> Europe/Middle East/Africa | Employees: 29,583 | Employee Breakdown by LOB and Corporate LOB: CB | Employee Breakdown by LOB and Corporate Employees: 17,867
> Latin America/Caribbean | Employees: 5,186 | Employee Breakdown by LOB and Corporate LOB: AWM | Employee Breakdown by LOB and Corporate Employees: 28,485
> Total Firm | Employees: 309,926 | Employee Breakdown by LOB and Corporate LOB: Corporate | Employee Breakdown by LOB and Corporate Employees: 47,530
> (row) | Employee Breakdown by LOB and Corporate LOB: Total Firm | Employee Breakdown by LOB and Corporate Employees: 309,926

**[3] JPMorgan Chase & Co. 10-K FY2024 — Item 1. Business (p. 10)**

> Table: As of December 31, 2024, JPMorganChase had 317,233 employees globally, an increase of 7,307 employees from the prior year. The increase was primarily attributable to growth in the number of front office and technology employees. JPMorganChase’s emplo
> North America | Employees: 187,179 | Employee Breakdown by LOB and Corporate LOB: CCB | Employee Breakdown by LOB and Corporate Employees: 144,989
> Asia-Pacific | Employees: 93,941 | Employee Breakdown by LOB and Corporate LOB: CIB | Employee Breakdown by LOB and Corporate Employees: 93,231
> Europe/Middle East/Africa | Employees: 30,729 | Employee Breakdown by LOB and Corporate LOB: AWM | Employee Breakdown by LOB and Corporate Employees: 29,403
> Latin America/Caribbean | Employees: 5,384 | Employee Breakdown by LOB and Corporate LOB: Corporate | Employee Breakdown by LOB and Corporate Employees: 49,610
> Total Firm | Employees: 317,233 | Employee Breakdown by LOB and Corporate LOB: Total Firm | Employee Breakdown by LOB and Corporate Employees: 317,233

**[4] JPMorgan Chase & Co. 10-K FY2024 — Item 1. Business (p. 10)**

> The increase was primarily attributable to growth in the number of front office and technology employees. JPMorganChase’s employees are located in 66 countries, with 59% of the Firm’s employees located in the U.S. The following table presents the distribution of the Firm’s global workforce by region and by line of business (“LOB”) and Corporate as of December 31, 2024:

**[5] JPMorgan Chase & Co. 10-K FY2025 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 74)**

> Table: (f)In the first quarter of 2025, 219 employees were transferred to Corporate as a result of the centralization of certain functions.
> Units: in millions, except ratios
> Nonaccrual loans to total period-end loans | 2025: 0.82 | 2024: 0.91 | 2023: 0.49

**[6] JPMorgan Chase & Co. 10-K FY2023 — Item 1. Business (p. 4)**

> The increase was primarily attributable to growth in front office, operations and technology, as well as the impact of the First Republic acquisition. The Firm’s employees are located in 65 countries, with 60% of the Firm’s employees located in the U.S. The following table presents the distribution of the Firm’s global workforce by region and by line of business (“LOB”) and Corporate as of December 31, 2023:

</details>

---

<!-- item: F08 judge: faithful -->
## 7. F08: Approximately how many employees did Johnson & Johnson have according to its 2023 10-K?

**Answer**

> Johnson & Johnson reported approximately **134,400 employees** in its 2023 Form 10‑K [1].

**Judge verdict: faithful.** The answer correctly cites the employee count of 134,400 from the 2023 10-K as stated in passage [1].

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] ★ Johnson & Johnson 10-K FY2023 — Item 1. Business (p. 11)**

> Table: As of December 31, 2023, the number of employees was approximately:
> Employees1 | 2023: 134,400
> Full-time equivalent (FTE) positions2 | 2023: 131,900

**[2] Johnson & Johnson 10-K FY2024 — Item 1. Business (p. 11)**

> Table: As of December 29, 2024 and December 31, 2023 the number of employees was approximately:
> Employees(1) | 2024: 139,800 | 2023: 134,400
> Full-time equivalent (FTE) positions(2) | 2024: 138,100 | 2023: 131,900

**[3] Johnson & Johnson 10-K FY2025 — Item 1. Business (p. 11)**

> Table: As of December 28, 2025 and December 29, 2024 the number of employees was approximately:
> Employees(1) | 2025: 140,800 | 2024: 139,800
> Full-time equivalent (FTE) positions(2) | 2025: 138,200 | 2024: 138,100

**[4] Johnson & Johnson 10-K FY2023 — Item 8. Financial statements and supplementary data (p. 49)**

> Table: Johnson & Johnson and subsidiaries consolidated balance sheets At December 31, 2023 and January 1, 2023 (Dollars in Millions Except Share and Per Share Amounts) (Note 1)
> Units: Dollars in Millions Except Share and Per Share Amounts
> Current liabilities > Accrued liabilities | 2023: 10,212 | 2022: 10,719
> Current liabilities > Accrued rebates, returns and promotions | 2023: 16,001 | 2022: 13,579
> Current liabilities > Accrued compensation and employee related obligations | 2023: 3,993 | 2022: 3,049
> Current liabilities > Accrued taxes on income (Note 8) | 2023: 2,993 | 2022: 2,220
> Current liabilities > Current liabilities of discontinued operations (Note 21) | 2023: — | 2022: 3,590
> Current liabilities > Total current liabilities | 2023: 46,282 | 2022: 55,802
> Long-term debt (Note 7) | 2023: 25,881 | 2022: 26,886
> Deferred taxes on income (Note 8) | 2023: 3,193 | 2022: 3,991
> Employee related obligations (Notes 9 and 10) | 2023: 7,149 | 2022: 6,542
> Long-term taxes payable (Note 1) | 2023: 2,881 | 2022: 4,306
> Other liabilities | 2023: 13,398 | 2022: 10,146
> Noncurrent liabilities of discontinued operations (Note 21) | 2023: — | 2022: 2,901
> Total liabilities | 2023: 98,784 | 2022: 110,574
> Shareholders’ equity > Preferred stock — without par value (authorized and unissued 2,000,000 shares) | 2023: — | 2022: —
> Shareholders’ equity > Common stock — par value $1.00 per share (Note 12) (authorized 4,320,000,000 shares; issued 3,119,843,000 shares) | 2023: 3,120 | 2022: 3,120

**[5] Johnson & Johnson 10-K FY2023 — Item 8. Financial statements and supplementary data (p. 91)**

> Units: Dollars in Millions
> Worldwide total | Sales to Customers 2023: $85,159 | Sales to Customers 2022: 79,990 | Sales to Customers 2021: 78,740 | Long-Lived Assets (6) 2023: $167,558 | Long-Lived Assets (6) 2022: 187,378

**[6] Johnson & Johnson 10-K FY2023 — Item 8. Financial statements and supplementary data (p. 91)**

> Units: Dollars in Millions
> United States | Sales to Customers 2023: $46,444 | Sales to Customers 2022: 41,981 | Sales to Customers 2021: 40,640 | Long-Lived Assets (6) 2023: $54,832 | Long-Lived Assets (6) 2022: 58,750
> Europe | Sales to Customers 2023: 20,410 | Sales to Customers 2022: 20,664 | Sales to Customers 2021: 20,595 | Long-Lived Assets (6) 2023: 31,616 | Long-Lived Assets (6) 2022: 29,878
> Western Hemisphere excluding U.S. | Sales to Customers 2023: 4,549 | Sales to Customers 2022: 4,108 | Sales to Customers 2021: 3,927 | Long-Lived Assets (6) 2023: 1,491 | Long-Lived Assets (6) 2022: 1,289
> Asia-Pacific, Africa | Sales to Customers 2023: 13,756 | Sales to Customers 2022: 13,237 | Sales to Customers 2021: 13,578 | Long-Lived Assets (6) 2023: 1,500 | Long-Lived Assets (6) 2022: 1,520
> Segments total | Sales to Customers 2023: 85,159 | Sales to Customers 2022: 79,990 | Sales to Customers 2021: 78,740 | Long-Lived Assets (6) 2023: 89,439 | Long-Lived Assets (6) 2022: 91,437
> Discontinued operations | Long-Lived Assets (6) 2023: — | Long-Lived Assets (6) 2022: 27,237
> General corporate | Long-Lived Assets (6) 2023: 1,192 | Long-Lived Assets (6) 2022: 1,081
> Other non long-lived assets | Long-Lived Assets (6) 2023: 76,927 | Long-Lived Assets (6) 2022: 67,623

</details>

---

<!-- item: F09 judge: faithful -->
## 8. F09: What business segments has Johnson & Johnson been organized into since the Kenvue separation?

**Answer**

> Johnson & Johnson has been organized into two business segments since the Kenvue separation: Innovative Medicine and MedTech[2†L1-L4][6†L13-L20]

**Judge verdict: faithful.** The answer correctly identifies the two business segments (Innovative Medicine and MedTech) and the timing (since the Kenvue separation) as explicitly stated in passages [2] and [6].

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] Johnson & Johnson 10-K FY2023 — Item 8. Financial statements and supplementary data (pp. 54–55)**

> See Notes to Consolidated Financial Statements
>
> Amounts presented have not been recast to exclude discontinued operations.
>
> Notes to Consolidated Financial Statements
>
> 1. Summary of significant accounting policies
>
> Principles of consolidation
>
> The consolidated financial statements include the accounts of Johnson & Johnson and its subsidiaries (the Company). Intercompany accounts and transactions are eliminated. Columns and rows within tables may not add due to rounding. Percentages have been calculated using actual, non-rounded figures.
>
> Description of the company and business segments
>
> The Company has approximately 131,900 employees worldwide engaged in the research and development, manufacture and sale of a broad range of products in the healthcare field. The Company conducts business in virtually all countries of the world and its primary focus is on products related to human health and well-being.
>
> Kenvue IPO/separation and discontinued operations
>
> On May 8, 2023, Kenvue, completed an initial public offering (the IPO) resulting in the issuance of 198,734,444 shares of its common stock, par value $0.01 per share (the “Kenvue Common Stock”), at an initial public offering of $22.00 per share for net proceeds of $4.2 billion. The excess of the net proceeds from the IPO over the net book value of the Johnson & Johnson divested interest was $2.5 billion and was recorded to additional paid-in capital. As of the closing of the IPO, Johnson & Johnson owned approximately 89.6% of the total outstanding shares of Kenvue Common Stock and at July 2, 2023, the non-controlling interest of $1.3 billion associated with Kenvue was reflected in equity attributable to non-controlling interests in the consolidated balance sheet in the fiscal second quarter of 2023.
>
> On August 23, 2023, Johnson & Johnson completed the disposition of an additional 80.1% ownership of the shares of Kenvue through an exchange offer. Following the exchange offer, the Company owns 9.5% of the shares of Kenvue which are accounted for as an equity investment carried at fair value within continuing operations. The historical results of the Consumer Health business (which previously represented the Consumer Health business segment) are reflected as discontinued operations in the Company’s Consolidated Financial Statements through the date of the exchange offer (see Note 21 for additional details).

**[2] ★ Johnson & Johnson 10-K FY2024 — Item 8. Financial statements and supplementary data (pp. 55–56)**

> The historical results of the Consumer Health business (which previously represented the Consumer Health business segment) are reflected as discontinued operations in the Company’s Consolidated Financial Statements through the date of the exchange offer (see Note 21 for additional details). Unless otherwise indicated, the information in the notes to the Consolidated Financial Statements refer only to Johnson & Johnson’s continuing operations.
>
> In the fiscal second quarter of 2024 the Company completed a debt for equity exchange of the retained stake in Kenvue. Upon completion of the debt for equity exchange, the Company no longer owns any shares of Kenvue Common Stock.
>
> Business segments
>
> The Company is organized into two business segments: Innovative Medicine and MedTech. The Innovative Medicine segment is focused on the following therapeutic areas: Immunology, Infectious Diseases, Neuroscience, Oncology, Pulmonary Hypertension, and Cardiovascular and Metabolic. Products in this segment are distributed directly to retailers, wholesalers, distributors, hospitals and healthcare professionals for prescription use. The MedTech segment includes a broad portfolio of products used in the Orthopaedic, Surgery, Cardiovascular (previously referred to as Interventional Solutions) and Vision fields. These products are distributed to wholesalers, hospitals and retailers, and used principally in the professional fields by physicians, nurses, hospitals, eye care professionals and clinics.
>
> New accounting standards
>
> Recently adopted accounting standards
>
> ASU 2023-07: Segment Reporting (Topic 280) – Improvements to Reportable Segment Disclosures
>
> The Company adopted the standard in the fiscal year 2024, which requires expanded annual and interim disclosures for significant segment expenses that are regularly provided to the chief operating decision maker and included within each reported measure of segment profit or loss. The standard was applied retrospectively to all periods presented in the financial statements. As this accounting standard only impacts disclosures, it did not have a material impact on the Company’s Consolidated Financial Statements. See Note 17 for the required disclosures.
>
> Recently issued accounting standards
>
> Not adopted as of December 29, 2024
>
> ASU 2024-03: Income Statement – Reporting Comprehensive Income – Expense Disaggregation Disclosures (Subtopic 220-40): Disaggregation of Income Statement Expenses
>
> This update requires disclosure of disaggregated information about certain income statement expense line items on an annual and interim basis. This update will be effective for fiscal years beginning after December 15, 2026, and interim periods within fiscal years beginning after December 15, 2027.

**[3] Johnson & Johnson 10-K FY2025 — Item 8. Financial statements and supplementary data (pp. 111–112)**

> Amounts related to the TSAs and TMAs included in the consolidated statements of earnings were immaterial for fiscal years 2025, 2024 and 2023. Additionally, the amounts due to and from Kenvue for the above agreements was not material as of December 28, 2025.
>
> The results of the Consumer Health business (previously reported as a separate business segment), as well as the associated gain, have been reflected as discontinued operations in the Company’s consolidated statements of earnings as Net earnings from discontinued operations, net of taxes. As a result of the separation of Kenvue, Johnson & Johnson incurred separation costs of $145 million in the fiscal year 2024, which was included in Net Earnings and incurred separation costs of $986 million in the fiscal year 2023, which were included in Net earnings from discontinued operations, net of taxes. These costs were primarily related to external advisory, legal, accounting, contractor and other incremental costs directly related to separation activities.
>
> Details of Net Earnings from Discontinued Operations, net of taxes are as follows:

**[4] Johnson & Johnson 10-K FY2024 — Item 8. Financial statements and supplementary data (pp. 110–111)**

> This one-time gain includes a gain of $2.8 billion on the Kenvue Common Stock retained by Johnson & Johnson. The gain on the exchange offer qualifies as a tax-free transaction for U.S. federal income tax purposes.
>
> Also in connection with the separation, Johnson & Johnson and Kenvue entered into a separation agreement and also entered into various other agreements that provide for certain transactions to effect the transfer of the assets and liabilities of the Consumer Health business to Kenvue and to govern various interim and ongoing relationships between Kenvue and Johnson & Johnson following the completion of the Kenvue IPO, including transition services agreements (TSAs), transition manufacturing agreements (TMAs), trademark agreements, intellectual property agreements, an employee matters agreement, and a tax matters agreement. Under the TSAs, Johnson & Johnson will provide Kenvue various services and, similarly, Kenvue will provide Johnson & Johnson various services. The provision of services under the TSAs generally will terminate within 24 months following the Kenvue IPO. Additionally, Johnson & Johnson and Kenvue entered into TMAs pursuant to which Johnson & Johnson will manufacture and supply to Kenvue certain products and, similarly, Kenvue will manufacture and supply to Johnson & Johnson certain products. The terms of the TMAs range in initial duration from 3 months to 5 years.
>
> Amounts related to the TSAs and TMAs included in the consolidated statements of earnings were immaterial for both fiscal years 2024 and 2023. Additionally, the amounts due to and from Kenvue for the above agreements was not material as of December 31, 2023.
>
> The results of the Consumer Health business (previously reported as a separate business segment), as well as the associated gain, have been reflected as discontinued operations in the Company’s consolidated statements of earnings as Net earnings from discontinued operations, net of taxes. As a result of the separation of Kenvue, Johnson & Johnson incurred separation costs of $145 million in the fiscal year 2024, which was included in Net Earnings and incurred separation costs of $986 million and $1,089 million in the fiscal years 2023 and 2022, respectively, which were included in Net earnings from discontinued operations, net of taxes. These costs were primarily related to external advisory, legal, accounting, contractor and other
>
> incremental costs directly related to separation activities.

**[5] Johnson & Johnson 10-K FY2023 — Item 8. Financial statements and supplementary data (pp. 107–108)**

> Amounts related to the TSAs and TMAs included in the consolidated statements of earnings were immaterial for the fiscal year 2023. Additionally, the amounts due to and from Kenvue for the above agreements was not material as of December 31, 2023.
>
> The results of the Consumer Health business (previously reported as a separate business segment), as well as the associated gain, have been reflected as discontinued operations in the Company’s consolidated statements of earnings as Net earnings from discontinued operations, net of taxes. Prior periods have been recast to reflect this presentation. As a result of the separation of Kenvue, Johnson & Johnson incurred separation costs of $986 million, $1,089 million and $67 million in the fiscal years 2023, 2022 and 2021, respectively, which are also included in Net earnings from discontinued operations, net of taxes. These costs were primarily related to external advisory, legal, accounting, contractor and other incremental costs directly related to separation activities. In the fiscal 2022, as part of the planned separation of the Company’s Consumer Health business, the Company recognized approximately $0.5 billion in net incremental tax costs. As of January 1, 2023, the assets and liabilities associated with the Consumer Health business were classified as assets and liabilities of discontinued operations in the consolidated balance sheets.
>
> Details of Net Earnings from Discontinued Operations, net of taxes are as follows:

**[6] ★ Johnson & Johnson 10-K FY2023 — Item 1. Business (p. 6)**

> General
>
> Johnson & Johnson and its subsidiaries (the Company) have approximately 131,900 employees worldwide engaged in the research and development, manufacture and sale of a broad range of products in the healthcare field. Johnson & Johnson is a holding company, with operating companies conducting business in virtually all countries of the world. The Company’s primary focus is products related to human health and well-being. Johnson & Johnson was incorporated in the State of New Jersey in 1887.
>
> The Executive Committee of Johnson & Johnson is the principal management group responsible for the strategic operations and allocation of the resources of the Company. This Committee oversees and coordinates the activities of the Company's two business segments: Innovative Medicine (previously referred to as Pharmaceutical) and MedTech. Within the strategic parameters provided by the Committee, senior management groups at U.S. and international operating companies are each responsible for their own strategic plans and the day-to-day operations of those companies. Each subsidiary within the business segments is, with limited exceptions, managed by residents of the country where located.
>
> Segments of business
>
> Following the completion of the separation of the Consumer Health business (Kenvue) in August 2023, the Company is now organized into two business segments: Innovative Medicine and MedTech. Additional information required by this item is incorporated herein by reference to the narrative and tabular descriptions of segments and operating results under: Item 7. Management’s discussion and analysis of results of operations and financial condition of this Report; and Note 17 Segments of business and geographic areas of the notes to consolidated financial statements included in Item 8 of this Report.
>
> Innovative Medicine
>
> The Innovative Medicine segment is focused on the following therapeutic areas: Immunology (e.g., rheumatoid arthritis, psoriatic arthritis, inflammatory bowel disease and psoriasis), Infectious Diseases (e.g., HIV/AIDS), Neuroscience (e.g., mood disorders, neurodegenerative disorders and schizophrenia), Oncology (e.g., prostate cancer, hematologic malignancies, lung cancer and bladder cancer), Cardiovascular and Metabolism (e.g., thrombosis, diabetes and macular degeneration) and Pulmonary Hypertension (e.g., Pulmonary Arterial Hypertension). Medicines in this segment are distributed directly to retailers, wholesalers, distributors, hospitals and healthcare professionals for prescription use.

</details>

---

<!-- item: F11 judge: faithful -->
## 9. F11: How much of its common stock did Apple repurchase during fiscal 2026?

**Answer**

> Apple repurchased 297 million shares of its common stock during fiscal 2026, costing $85.8 billion [1].

**Judge verdict: faithful.** The answer correctly cites the number of shares (297 million) and the cost ($85.8 billion) repurchased during 2026 as stated in passage [1].

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] ★ Apple Inc. 10-K FY2026 — Item 8. Financial Statements and Supplementary Data (p. 51)**

> As of September 26, 2026 and September 27, 2025, the fair value of the Company’s Notes, based on Level 2 inputs, was $64.0 billion and $80.4 billion, respectively.
>
> Note 11 – Shareholders’ Equity
>
> Share Repurchase Program
>
> During 2026, the Company repurchased 297 million shares of its common stock for $85.8 billion. The Company’s share repurchase programs do not obligate the Company to acquire a minimum amount of shares. Under the programs, shares may be repurchased in privately negotiated or open market transactions, including under plans complying with Rule 10b5-1 under the Exchange Act.
>
> Shares of Common Stock
>
> The following table shows the changes in shares of common stock for 2026, 2025 and 2024 (in thousands):

**[2] Apple Inc. 10-K FY2025 — Item 8. Financial Statements and Supplementary Data (pp. 46–47)**

> As of September 27, 2025 and September 28, 2024, the fair value of the Company’s Notes, based on Level 2 inputs, was $80.4 billion and $88.4 billion, respectively.
>
> Note 10 – Shareholders’ Equity
>
> Share Repurchase Program
>
> During 2025, the Company repurchased 402 million shares of its common stock for $89.3 billion. The Company’s share repurchase programs do not obligate the Company to acquire a minimum amount of shares. Under the programs, shares may be repurchased in privately negotiated or open market transactions, including under plans complying with Rule 10b5-1 under the Exchange Act.
>
> Shares of Common Stock
>
> The following table shows the changes in shares of common stock for 2025, 2024 and 2023 (in thousands):

**[3] Apple Inc. 10-K FY2024 — Item 8. Financial Statements and Supplementary Data (p. 46)**

> As of September 28, 2024 and September 30, 2023, the fair value of the Company’s Notes, based on Level 2 inputs, was $88.4 billion and $90.8 billion, respectively.
>
> Note 10 – Shareholders’ Equity
>
> Share Repurchase Program
>
> During 2024, the Company repurchased 499 million shares of its common stock for $95.0 billion. The Company’s share repurchase programs do not obligate the Company to acquire a minimum amount of shares. Under the programs, shares may be repurchased in privately negotiated or open market transactions, including under plans complying with Rule 10b5-1 under the Exchange Act.
>
> Shares of Common Stock
>
> The following table shows the changes in shares of common stock for 2024, 2023 and 2022 (in thousands):

**[4] Apple Inc. 10-K FY2026 — Item 5. Market for Registrant’s Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities (pp. 24–25)**

> (1)On May 1, 2025, the Company announced a program to repurchase up to $100 billion of the Company’s common stock. As of September 26, 2026, remaining availability under the May 2025 program was $14.0 billion. On April 30, 2026, the Company announced an additional program to repurchase up to $100 billion of the Company’s common stock. The programs do not obligate the Company to acquire a minimum amount of shares. Under the programs, shares may be repurchased in privately negotiated or open market transactions, including under plans complying with Rule 10b5-1 under the Exchange Act.
>
> (2)In May 2026, the Company entered into accelerated share repurchase agreements (“ASRs”). Under the terms of the ASRs, financial institutions committed to deliver shares of the Company’s common stock during the purchase periods in exchange for up-front payments totaling $10.0 billion. In August 2026, the purchase periods for the ASRs ended and 6 million shares were delivered and retired. In total, 33 million shares were delivered under the ASRs at an average repurchase price of $305.29 per share.
>
> Company Stock Performance
>
> The following graph shows a comparison of five-year cumulative total shareholder return, calculated on a dividend-reinvested basis, for the Company, the S&P 500 Index and the Dow Jones U.S. Technology Total Stock Market Index. The graph assumes $100 was invested in each of the Company’s common stock, the S&P 500 Index and the Dow Jones U.S. Technology Total Stock Market Index as of the market close on September 24, 2021. Past stock price performance is not necessarily indicative of future stock price performance.

**[5] Apple Inc. 10-K FY2025 — Item 5. Market for Registrant’s Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities (pp. 21–22)**

> (1)On May 2, 2024, the Company announced a program to repurchase up to $110 billion of the Company’s common stock. During the fourth quarter of 2025, the Company utilized the final $19.8 billion under the May 2024 program. On May 1, 2025, the Company announced an additional program to repurchase up to $100 billion of the Company’s common stock. As of September 27, 2025, $221 million of the May 2025 program had been utilized. The programs do not obligate the Company to acquire a minimum amount of shares. Under the programs, shares may be repurchased in privately negotiated or open market transactions, including under plans complying with Rule 10b5-1 under the Exchange Act.
>
> Company Stock Performance
>
> The following graph shows a comparison of five-year cumulative total shareholder return, calculated on a dividend-reinvested basis, for the Company, the S&P 500 Index and the Dow Jones U.S. Technology Total Stock Market Index. The graph assumes $100 was invested in each of the Company’s common stock, the S&P 500 Index and the Dow Jones U.S. Technology Total Stock Market Index as of the market close on September 25, 2020. Past stock price performance is not necessarily indicative of future stock price performance.

**[6] Apple Inc. 10-K FY2024 — Item 5. Market for Registrant’s Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities (pp. 21–22)**

> (1)As of September 28, 2024, the Company was authorized by the Board to purchase up to $110 billion of the Company’s common stock under a share repurchase program announced on May 2, 2024, of which $20.9 billion had been utilized. During the fourth quarter of 2024, the Company also utilized the final $4.1 billion under its previous repurchase program, which was authorized in May 2023. The programs do not obligate the Company to acquire a minimum amount of shares. Under the programs, shares may be repurchased in privately negotiated or open market transactions, including under plans complying with Rule 10b5-1 under the Exchange Act.
>
> Company Stock Performance
>
> The following graph shows a comparison of five-year cumulative total shareholder return, calculated on a dividend-reinvested basis, for the Company, the S&P 500 Index and the Dow Jones U.S. Technology Supersector Index. The graph assumes $100 was invested in each of the Company’s common stock, the S&P 500 Index and the Dow Jones U.S. Technology Supersector Index as of the market close on September 27, 2019. Past stock price performance is not necessarily indicative of future stock price performance.

</details>

---

<!-- item: T01 judge: faithful -->
## 10. T01: What were Apple's iPhone net sales in fiscal 2026?

**Answer**

> Apple’s iPhone net sales in fiscal 2026 were **$254,098 million**[4].

**Judge verdict: faithful.** The answer correctly cites the specific figure for iPhone net sales in fiscal 2026 ($254,098 million) found in passage [4].

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] Apple Inc. 10-K FY2026 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 28–29)**

> (1)Services net sales include amortization of the deferred value of services bundled in the sales price of certain products.
>
> iPhone
>
> iPhone net sales increased during 2026 compared to 2025 due to higher net sales of Pro models.
>
> Mac
>
> Mac net sales increased during 2026 compared to 2025 due to higher net sales of laptops.
>
> iPad
>
> iPad net sales during 2026 compared to 2025 were relatively flat.
>
> Wearables, Home and Accessories
>
> Wearables, Home and Accessories net sales during 2026 compared to 2025 were relatively flat.
>
> Services
>
> Services net sales increased during 2026 compared to 2025 primarily due to higher net sales from advertising and cloud services.
>
> Gross Margin
>
> Products and Services gross margin and gross margin percentage for 2026, 2025 and 2024 were as follows (dollars in millions):

**[2] Apple Inc. 10-K FY2024 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 25–26)**

> (1)Services net sales include amortization of the deferred value of services bundled in the sales price of certain products.
>
> iPhone
>
> iPhone net sales were relatively flat during 2024 compared to 2023.
>
> Mac
>
> Mac net sales increased during 2024 compared to 2023 due primarily to higher net sales of laptops.
>
> iPad
>
> iPad net sales decreased during 2024 compared to 2023 due primarily to lower net sales of iPad Pro and the entry-level iPad models, partially offset by higher net sales of iPad Air.
>
> Wearables, Home and Accessories
>
> Wearables, Home and Accessories net sales decreased during 2024 compared to 2023 due primarily to lower net sales of Wearables and Accessories.
>
> Services
>
> Services net sales increased during 2024 compared to 2023 due primarily to higher net sales from advertising, the App Store® and cloud services.
>
> Gross Margin
>
> Products and Services gross margin and gross margin percentage for 2024, 2023 and 2022 were as follows (dollars in millions):

**[3] Apple Inc. 10-K FY2025 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 25–26)**

> (1)Services net sales include amortization of the deferred value of services bundled in the sales price of certain products.
>
> iPhone
>
> iPhone net sales increased during 2025 compared to 2024 due to higher net sales of Pro models.
>
> Mac
>
> Mac net sales increased during 2025 compared to 2024 primarily due to higher net sales of laptops and desktops.
>
> iPad
>
> iPad net sales increased during 2025 compared to 2024 primarily due to higher net sales of iPad Air, iPad mini and iPad, partially offset by lower net sales of iPad Pro.
>
> Wearables, Home and Accessories
>
> Wearables, Home and Accessories net sales decreased during 2025 compared to 2024 primarily due to lower net sales of Accessories and Wearables.
>
> Services
>
> Services net sales increased during 2025 compared to 2024 primarily due to higher net sales from advertising, the App Store and cloud services.
>
> Gross Margin
>
> Products and Services gross margin and gross margin percentage for 2025, 2024 and 2023 were as follows (dollars in millions):

**[4] ★ Apple Inc. 10-K FY2026 — Item 8. Financial Statements and Supplementary Data (p. 41)**

> Table: The following table shows disaggregated net sales, as well as the portion of total net sales that was previously deferred, for 2026, 2025 and 2024 (in millions):
> Units: in millions
> iPhone | 2026: $254,098 | 2025: $209,586 | 2024: $201,183
> Mac | 2026: 37,929 | 2025: 33,708 | 2024: 29,984
> iPad | 2026: 27,929 | 2025: 28,023 | 2024: 26,694
> Wearables, Home and Accessories | 2026: 35,577 | 2025: 35,686 | 2024: 37,005
> Services (1) | 2026: 123,301 | 2025: 109,158 | 2024: 96,169
> Total net sales | 2026: $478,834 | 2025: $416,161 | 2024: $391,035
> Portion of total net sales that was included in deferred revenue as of the beginning of the period | 2026: $8,717 | 2025: $8,229 | 2024: $7,728

**[5] Apple Inc. 10-K FY2026 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 27–28)**

> Americas
>
> Americas net sales increased during 2026 compared to 2025 due to higher net sales of iPhone, Services and Mac.
>
> Europe
>
> Europe net sales increased during 2026 compared to 2025 primarily due to higher net sales of iPhone, Services and Mac. The strength in foreign currencies relative to the U.S. dollar had a net favorable year-over-year impact on Europe net sales during 2026.
>
> Greater China
>
> Greater China net sales increased during 2026 compared to 2025 primarily due to higher net sales of iPhone and Mac. The strength in the renminbi relative to the U.S. dollar had a favorable year-over-year impact on Greater China net sales during 2026.
>
> Japan
>
> Japan net sales increased during 2026 compared to 2025 due to higher net sales of iPhone. The weakness in the yen relative to the U.S. dollar had an unfavorable year-over-year impact on Japan net sales during 2026.
>
> Rest of Asia Pacific
>
> Rest of Asia Pacific net sales increased during 2026 compared to 2025 primarily due to higher net sales of iPhone, Services and Mac.
>
> Products and Services Performance
>
> The following table shows net sales by category for 2026, 2025 and 2024 (dollars in millions):

**[6] Apple Inc. 10-K FY2026 — Item 8. Financial Statements and Supplementary Data (p. 41)**

> (1)Services net sales include amortization of the deferred value of services bundled in the sales price of certain products.
>
> The Company’s proportion of net sales by disaggregated revenue source was generally consistent for each reportable segment (refer to Note 14, “Segment Information and Geographic Data”) for 2026, 2025 and 2024, except in Greater China, where iPhone revenue represented a moderately higher proportion of net sales. In addition, in 2026, Services revenue represented a moderately lower proportion of net sales in Greater China.
>
> As of September 26, 2026 and September 27, 2025, the Company had total deferred revenue of $14.8 billion and $13.7 billion, respectively. As of September 26, 2026, the Company expects 65% of total deferred revenue to be realized in less than a year, 22% within one-to-two years, 11% within two-to-three years and 2% in greater than three years.
>
> Note 3 – Earnings Per Share
>
> The following table shows the computation of basic and diluted earnings per share for 2026, 2025 and 2024 (net income in millions and shares in thousands):

</details>

---

<!-- item: T02 judge: faithful -->
## 11. T02: What were Apple's net sales in Greater China in fiscal 2026?

**Answer**

> Apple’s net sales in Greater China for fiscal 2026 were $82,378 million[4].

**Judge verdict: faithful.** The answer correctly cites the net sales figure of $82,378 million for Greater China in 2026 from passage [4].

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] Apple Inc. 10-K FY2026 — Item 8. Financial Statements and Supplementary Data (p. 41)**

> (1)Services net sales include amortization of the deferred value of services bundled in the sales price of certain products.
>
> The Company’s proportion of net sales by disaggregated revenue source was generally consistent for each reportable segment (refer to Note 14, “Segment Information and Geographic Data”) for 2026, 2025 and 2024, except in Greater China, where iPhone revenue represented a moderately higher proportion of net sales. In addition, in 2026, Services revenue represented a moderately lower proportion of net sales in Greater China.
>
> As of September 26, 2026 and September 27, 2025, the Company had total deferred revenue of $14.8 billion and $13.7 billion, respectively. As of September 26, 2026, the Company expects 65% of total deferred revenue to be realized in less than a year, 22% within one-to-two years, 11% within two-to-three years and 2% in greater than three years.
>
> Note 3 – Earnings Per Share
>
> The following table shows the computation of basic and diluted earnings per share for 2026, 2025 and 2024 (net income in millions and shares in thousands):

**[2] Apple Inc. 10-K FY2026 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 27–28)**

> Americas
>
> Americas net sales increased during 2026 compared to 2025 due to higher net sales of iPhone, Services and Mac.
>
> Europe
>
> Europe net sales increased during 2026 compared to 2025 primarily due to higher net sales of iPhone, Services and Mac. The strength in foreign currencies relative to the U.S. dollar had a net favorable year-over-year impact on Europe net sales during 2026.
>
> Greater China
>
> Greater China net sales increased during 2026 compared to 2025 primarily due to higher net sales of iPhone and Mac. The strength in the renminbi relative to the U.S. dollar had a favorable year-over-year impact on Greater China net sales during 2026.
>
> Japan
>
> Japan net sales increased during 2026 compared to 2025 due to higher net sales of iPhone. The weakness in the yen relative to the U.S. dollar had an unfavorable year-over-year impact on Japan net sales during 2026.
>
> Rest of Asia Pacific
>
> Rest of Asia Pacific net sales increased during 2026 compared to 2025 primarily due to higher net sales of iPhone, Services and Mac.
>
> Products and Services Performance
>
> The following table shows net sales by category for 2026, 2025 and 2024 (dollars in millions):

**[3] Apple Inc. 10-K FY2024 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 24–25)**

> Americas
>
> Americas net sales increased during 2024 compared to 2023 due primarily to higher net sales of Services.
>
> Europe
>
> Europe net sales increased during 2024 compared to 2023 due primarily to higher net sales of Services and iPhone.
>
> Greater China
>
> Greater China net sales decreased during 2024 compared to 2023 due primarily to lower net sales of iPhone and iPad. The weakness in the renminbi relative to the U.S. dollar had an unfavorable year-over-year impact on Greater China net sales during 2024.
>
> Japan
>
> Japan net sales increased during 2024 compared to 2023 due primarily to higher net sales of iPhone. The weakness in the yen relative to the U.S. dollar had an unfavorable year-over-year impact on Japan net sales during 2024.
>
> Rest of Asia Pacific
>
> Rest of Asia Pacific net sales increased during 2024 compared to 2023 due primarily to higher net sales of Services. The weakness in foreign currencies relative to the U.S. dollar had a net unfavorable year-over-year impact on Rest of Asia Pacific net sales during 2024.
>
> Products and Services Performance
>
> The following table shows net sales by category for 2024, 2023 and 2022 (dollars in millions):

**[4] ★ Apple Inc. 10-K FY2026 — Item 8. Financial Statements and Supplementary Data (p. 55)**

> Table: The following tables show net sales for 2026, 2025 and 2024 and long-lived assets as of September 26, 2026 and September 27, 2025 for countries that individually accounted for 10% or more of the respective totals, as well as aggregate amounts for the
> Net sales > U.S. | 2026: $167,746 | 2025: $151,790 | 2024: $142,196
> Net sales > China (1) | 2026: 82,378 | 2025: 64,377 | 2024: 66,952
> Net sales > Other countries | 2026: 228,710 | 2025: 199,994 | 2024: 181,887
> Net sales > Total net sales | 2026: $478,834 | 2025: $416,161 | 2024: $391,035

**[5] Apple Inc. 10-K FY2025 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 24–25)**

> Americas
>
> Americas net sales increased during 2025 compared to 2024 primarily due to higher net sales of iPhone and Services. The weakness in foreign currencies relative to the U.S. dollar had an unfavorable year-over-year impact on Americas net sales during 2025.
>
> Europe
>
> Europe net sales increased during 2025 compared to 2024 primarily due to higher net sales of Services, iPhone and Mac.
>
> Greater China
>
> Greater China net sales decreased during 2025 compared to 2024 primarily due to lower net sales of iPhone, partially offset by higher net sales of Mac.
>
> Japan
>
> Japan net sales increased during 2025 compared to 2024 primarily due to higher net sales of iPhone, Services and iPad.
>
> Rest of Asia Pacific
>
> Rest of Asia Pacific net sales increased during 2025 compared to 2024 primarily due to higher net sales of iPhone, Services and Mac.
>
> Products and Services Performance
>
> The following table shows net sales by category for 2025, 2024 and 2023 (dollars in millions):

**[6] Apple Inc. 10-K FY2026 — Item 8. Financial Statements and Supplementary Data (p. 54)**

> Net sales | 2025 Americas: $178,353 | 2025 Europe: $111,032 | 2025 Greater China: $64,377 | 2025 Japan: $28,703 | 2025 Rest of Asia Pacific: $33,696 | 2025 Corporate: $— | 2025 Total: $416,161
> Cost of sales | 2025 Americas: (95,699) | 2025 Europe: (58,617) | 2025 Greater China: (35,141) | 2025 Japan: (13,779) | 2025 Rest of Asia Pacific: (17,724) | 2025 Corporate: — | 2025 Total: (220,960)
> Research and development | 2025 Americas: — | 2025 Europe: — | 2025 Greater China: — | 2025 Japan: — | 2025 Rest of Asia Pacific: — | 2025 Corporate: (34,550) | 2025 Total: (34,550)
> Selling and marketing | 2025 Americas: (10,174) | 2025 Europe: (4,676) | 2025 Greater China: (2,319) | 2025 Japan: (969) | 2025 Rest of Asia Pacific: (1,386) | 2025 Corporate: — | 2025 Total: (19,524)
> General and administrative | 2025 Americas: — | 2025 Europe: — | 2025 Greater China: — | 2025 Japan: — | 2025 Rest of Asia Pacific: — | 2025 Corporate: (8,077) | 2025 Total: (8,077)
> Operating income/(loss) | 2025 Americas: $72,480 | 2025 Europe: $47,739 | 2025 Greater China: $26,917 | 2025 Japan: $13,955 | 2025 Rest of Asia Pacific: $14,586 | 2025 Corporate: $(42,627) | 2025 Total: $133,050

</details>

---

<!-- item: T07 judge: faithful -->
## 12. T07: What was Amazon's total operating income in 2025?

**Answer**

> Amazon’s total operating income in 2025 was about $80.0 billion [2] (the segment table shows a consolidated operating income of $79,975 million for 2025 [3]).

**Judge verdict: faithful.** The answer correctly cites the $80.0 billion figure from passage [2] and the specific $79,975 million figure from the table in passage [3], both of which are explicitly stated in the source text.

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] Amazon.com, Inc. 10-K FY2023 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 25–26)**

> Operating income was $12.2 billion and $36.9 billion for 2022 and 2023. We believe that operating income is a more meaningful measure than gross profit and gross margin due to the diversity of our product categories and services.
>
> The North America operating income in 2023, as compared to the operating loss in the prior year, is primarily due to increased unit sales and increased advertising sales, partially offset by increased shipping and fulfillment costs and increased technology and infrastructure costs.
>
> The decrease in International operating loss in absolute dollars in 2023, compared to the prior year, is primarily due to increased unit sales and increased advertising sales, partially offset by increased fulfillment and shipping costs and increased technology and infrastructure costs. Changes in foreign exchange rates positively impacted operating loss by $246 million in 2023.
>
> The increase in AWS operating income in absolute dollars in 2023, compared to the prior year, is primarily due to increased sales, partially offset by increased payroll and related expenses and spending on technology infrastructure, both of which were primarily driven by additional investments to support AWS business growth. Changes in foreign exchange rates positively impacted operating income by $220 million in 2023.
>
> Operating Expenses
>
> Information about operating expenses is as follows (in millions):

**[2] ★ Amazon.com, Inc. 10-K FY2025 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 27)**

> Operating income was $68.6 billion and $80.0 billion for 2024 and 2025. Operating income for 2025 includes charges of $2.5 billion we recorded in Q3 2025 related to the settlement of a lawsuit with the FTC and $2.7 billion, of which $1.8 billion was recorded in Q3 2025, of estimated severance costs primarily related to planned role eliminations. We believe that operating income is a more meaningful measure than gross profit and gross margin due to the diversity of our product categories and services. For more information on the operating expenses that impact segment operating income, see “Operating Expenses” and the descriptions of operating expense line item changes on pages 25 to 27, and “Note 10 — Segment Information” on page 67.
>
> The increase in North America operating income in 2025, compared to the prior year, is primarily due to increased unit sales and increased advertising sales, partially offset by increased fulfillment, technology and infrastructure, shipping, and other operating costs. Changes in foreign exchange rates negatively impacted operating income by $204 million in 2025.
>
> The increase in International operating income in 2025, compared to the prior year, is primarily due to increased unit sales and increased advertising sales, partially offset by increased fulfillment and shipping costs. Changes in foreign exchange rates positively impacted operating income by $903 million in 2025.
>
> The increase in AWS operating income in 2025, compared to the prior year, is primarily due to increased sales, partially offset by spending on technology infrastructure that was primarily driven by additional investments to support AWS business growth. Changes in foreign exchange rates negatively impacted operating income by $341 million in 2025.
>
> Interest Income and Expense
>
> Our interest income was $4.7 billion and $4.4 billion during 2024 and 2025, primarily due to a decrease in prevailing rates, offset by a higher average balance of invested funds. We generally invest our excess cash in investment grade short- to intermediate-term marketable debt securities and AAA-rated money market funds. Our interest income corresponds with the average balance of invested funds based on the prevailing rates, which vary depending on the geographies and currencies in which they are invested.
>
> Interest expense was $2.4 billion and $2.3 billion in 2024 and 2025 and was primarily related to debt and finance leases.

**[3] ★ Amazon.com, Inc. 10-K FY2025 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 27)**

> Table: Operating income by segment is as follows (in millions):
> Units: in millions
> Operating Income > North America | Year Ended December 31, 2024: $24,967 | Year Ended December 31, 2025: $29,619
> Operating Income > International | Year Ended December 31, 2024: 3,792 | Year Ended December 31, 2025: 4,750
> Operating Income > AWS | Year Ended December 31, 2024: 39,834 | Year Ended December 31, 2025: 45,606
> Operating Income > Consolidated | Year Ended December 31, 2024: $68,593 | Year Ended December 31, 2025: $79,975

**[4] Amazon.com, Inc. 10-K FY2024 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 27)**

> Operating income was $36.9 billion and $68.6 billion for 2023 and 2024. We believe that operating income is a more meaningful measure than gross profit and gross margin due to the diversity of our product categories and services. For more information on the operating expenses that impact segment operating income, see “Operating Expenses” and the descriptions of operating expense line item changes on pages 25 to 27, and “Note 10 — Segment Information” on page 65.
>
> The increase in North America operating income in 2024, compared to the prior year, is primarily due to increased unit sales and increased advertising sales, partially offset by increased fulfillment and shipping costs.
>
> The International operating income in 2024, as compared to the operating loss in the prior year, is primarily due to increased unit sales and increased advertising sales, partially offset by increased shipping and fulfillment costs. Changes in foreign exchange rates did not significantly impact operating income in 2024.
>
> The increase in AWS operating income in 2024, compared to the prior year, is primarily due to increased sales, decreased payroll and related expenses, and a reduction in depreciation and amortization expense from our change in the estimated useful lives of our servers, partially offset by spending on technology infrastructure that was primarily driven by additional investments to support AWS business growth. Changes in foreign exchange rates positively impacted operating income by $240 million in 2024.
>
> Interest Income and Expense
>
> Our interest income was $2.9 billion and $4.7 billion during 2023 and 2024, primarily due to a higher average balance of invested funds at prevailing rates. We generally invest our excess cash in investment grade short- to intermediate-term marketable debt securities and AAA-rated money market funds. Our interest income corresponds with the average balance of invested funds based on the prevailing rates, which vary depending on the geographies and currencies in which they are invested.
>
> Interest expense was $3.2 billion and $2.4 billion in 2023 and 2024 and was primarily related to debt and finance leases. See Item 8 of Part II, “Financial Statements and Supplementary Data — Note 4 — Leases and Note 6 — Debt” for additional information.
>
> Our long-term lease liabilities were $77.3 billion and $78.3 billion as of December 31, 2023 and 2024.

**[5] Amazon.com, Inc. 10-K FY2024 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 27)**

> Table: Operating income (loss) by segment is as follows (in millions):
> Units: in millions
> Operating Income (Loss) > North America | Year Ended December 31, 2023: $14,877 | Year Ended December 31, 2024: $24,967
> Operating Income (Loss) > International | Year Ended December 31, 2023: (2,656) | Year Ended December 31, 2024: 3,792
> Operating Income (Loss) > AWS | Year Ended December 31, 2023: 24,631 | Year Ended December 31, 2024: 39,834
> Operating Income (Loss) > Consolidated | Year Ended December 31, 2023: $36,852 | Year Ended December 31, 2024: $68,593

**[6] Amazon.com, Inc. 10-K FY2023 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 25)**

> Table: Operating income (loss) by segment is as follows (in millions):
> Units: in millions
> Operating Income (Loss) > North America | Year Ended December 31, 2022: $(2,847) | Year Ended December 31, 2023: $14,877
> Operating Income (Loss) > International | Year Ended December 31, 2022: (7,746) | Year Ended December 31, 2023: (2,656)
> Operating Income (Loss) > AWS | Year Ended December 31, 2022: 22,841 | Year Ended December 31, 2023: 24,631
> Operating Income (Loss) > Consolidated | Year Ended December 31, 2022: $12,248 | Year Ended December 31, 2023: $36,852

</details>

---

<!-- item: T08 judge: faithful -->
## 13. T08: What was JPMorgan Chase's Standardized CET1 capital ratio at December 31, 2025?

**Answer**

> JPMorgan Chase’s Standardized CET1 capital ratio was **14.6 %** at December 31, 2025[3].

**Judge verdict: faithful.** The answer correctly cites the Standardized CET1 capital ratio of 14.6% for December 31, 2025, which is explicitly stated in passage [3].

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] JPMorgan Chase & Co. 10-K FY2024 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 104)**

> (a)The capital metrics reflect the CECL capital transition provisions. As of December 31, 2024, CET1 capital reflected the remaining $720 million CECL benefit and were fully phased in as of January 1, 2025; as of December 31, 2023, CET1 capital reflected a $1.4 billion benefit. Refer to Note 27 for additional information.
>
> (b)Represents minimum requirements and regulatory buffers applicable to the Firm for the period ended December 31, 2024. For the period ended December 31, 2023, the Basel III Standardized CET1, Tier 1, and Total capital ratio requirements applicable to the Firm were 11.4%, 12.9%, and 14.9%, respectively; the Basel III Advanced CET1, Tier 1, and Total capital ratio requirements applicable to the Firm were 11.0%, 12.5%, and 14.5%, respectively. Refer to Note 27 for additional information.
>
> (c)Includes the impacts of certain assets associated with First Republic to which the Standardized approach has been applied as permitted by the transition provisions in the U.S. capital rules.

**[2] JPMorgan Chase & Co. 10-K FY2023 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 98)**

> (a)The capital metrics reflect the CECL capital transition provisions. Refer to Note 27 for additional information.
>
> (b)Represents minimum requirements and regulatory buffers applicable to the Firm for the period ended December 31, 2023. For the period ended December 31, 2022, the Basel III Standardized CET1, Tier 1, and Total capital ratio requirements applicable to the Firm were 12.0%, 13.5%, and 15.5%, respectively; the Basel III Advanced CET1, Tier 1, and Total capital ratio requirements applicable to the Firm were 10.5%, 12.0%, and 14.0%, respectively. Refer to Note 27 for additional information.
>
> (c)Includes the impacts of certain assets associated with First Republic to which the Standardized approach has been applied as permitted by the transition provisions in the U.S. capital rules.

**[3] ★ JPMorgan Chase & Co. 10-K FY2025 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 96)**

> Table: The following tables present the Firm’s risk-based capital metrics under both the Standardized and Advanced approaches and leverage-based capital metrics. Refer to Note 27 for JPMorgan Chase Bank, N.A.’s risk-based and leverage-based capital metrics.
> Units: in millions, except ratios
> Risk-based capital metrics > CET1 capital | Standardized December 31, 2025: $288,469 | Standardized December 31, 2024: $275,513 | Advanced December 31, 2025: $288,469 | Advanced December 31, 2024: $275,513
> Risk-based capital metrics > Tier 1 capital | Standardized December 31, 2025: 307,630 | Standardized December 31, 2024: 294,881 | Advanced December 31, 2025: 307,630 | Advanced December 31, 2024: 294,881
> Risk-based capital metrics > Total capital | Standardized December 31, 2025: 343,843 | Standardized December 31, 2024: 325,589 | Advanced December 31, 2025: 328,962 | Advanced December 31, 2024: 311,898
> Risk-weighted assets | Standardized December 31, 2025: 1,981,692 | Standardized December 31, 2024: 1,757,460 | Standardized Capital ratio requirements(d): 2,045,249 | Advanced December 31, 2025: (b)(e) | Advanced December 31, 2024: 1,740,429
> CET1 capital ratio | Standardized December 31, 2025: 14.6% | Standardized December 31, 2024: 15.7% | Standardized Capital ratio requirements(d): 11.5% | Advanced December 31, 2025: 14.1% | Advanced December 31, 2024: 15.8% | Advanced Capital ratio requirements(d): 11.5%
> Tier 1 capital ratio | Standardized December 31, 2025: 15.5 | Standardized December 31, 2024: 16.8 | Standardized Capital ratio requirements(d): 13.0 | Advanced December 31, 2025: 15.0 | Advanced December 31, 2024: 16.9 | Advanced Capital ratio requirements(d): 13.0

**[4] JPMorgan Chase & Co. 10-K FY2025 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 97)**

> Table: The following table presents reconciliations of total stockholders’ equity to CET1 capital, Tier 1 capital and Total capital as of December 31, 2025 and 2024.
> Units: in millions
> Less > Standardized Tier 2 capital | December 31, 2025: $36,213 | December 31, 2024: $30,708
> Less > Standardized Total capital | December 31, 2025: $343,843 | December 31, 2024: $325,589
> Less > Adjustment in qualifying allowance for credit losses for Advanced Tier 2 capital | December 31, 2025: (14,881) | December 31, 2024: (13,691)
> Less > Advanced Tier 2 capital | December 31, 2025: $21,332 | December 31, 2024: $17,017
> Less > Advanced Total capital | December 31, 2025: $328,962 | December 31, 2024: $311,898

**[5] JPMorgan Chase & Co. 10-K FY2024 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 104)**

> Table: The following tables present the Firm’s risk-based capital metrics under both the Basel III Standardized and Advanced approaches and leverage-based capital metrics. Refer to Note 27 for JPMorgan Chase Bank, N.A.’s risk-based and leverage-based capita
> Units: in millions, except ratios
> Risk-based capital metrics > CET1 capital | Standardized December 31, 2024: $275,513 | Standardized December 31, 2023: $250,585 | Advanced December 31, 2024: $275,513 | Advanced December 31, 2023: $250,585
> Risk-based capital metrics > Tier 1 capital | Standardized December 31, 2024: 294,881 | Standardized December 31, 2023: 277,306 | Advanced December 31, 2024: 294,881 | Advanced December 31, 2023: 277,306
> Risk-based capital metrics > Total capital | Standardized December 31, 2024: 325,589 | Standardized December 31, 2023: 308,497 | Advanced December 31, 2024: 311,898 | Advanced December 31, 2023: 295,417
> Risk-weighted assets | Standardized December 31, 2024: 1,757,460 | Standardized December 31, 2023: 1,671,995 | Advanced December 31, 2024: 1,740,429 | Advanced December 31, 2023: 1,669,156
> CET1 capital ratio | Standardized December 31, 2024: 15.7% | Standardized December 31, 2023: 15.0% | Standardized Capital ratio requirements(b): 12.3% | Advanced December 31, 2024: 15.8% | Advanced December 31, 2023: 15.0% | Advanced Capital ratio requirements(b): 11.5%
> Tier 1 capital ratio | Standardized December 31, 2024: 16.8 | Standardized December 31, 2023: 16.6 | Standardized Capital ratio requirements(b): 13.8 | Advanced December 31, 2024: 16.9 | Advanced December 31, 2023: 16.6 | Advanced Capital ratio requirements(b): 13.0

**[6] JPMorgan Chase & Co. 10-K FY2025 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 97)**

> Table: The following table presents the changes in CET1 capital, Tier 1 capital and Tier 2 capital for the year ended December 31, 2025.
> Units: in millions
> Standardized/Advanced CET1 capital at December 31, 2024 | 2025: $275,513
> Net income applicable to common equity | 2025: 55,949
> Dividends declared on common stock | 2025: (16,060)
> Net purchase of treasury stock | 2025: (30,573)
> Changes in additional paid-in capital | 2025: 203
> Changes related to AOCI applicable to capital > Unrealized gains/(losses) on investment securities | 2025: 3,569
> Changes related to AOCI applicable to capital > Translation adjustments, net of hedges | 2025: 1,339
> Changes related to AOCI applicable to capital > Fair value hedges | 2025: 64
> Changes related to AOCI applicable to capital > Defined benefit pension and other postretirement employee benefit (“OPEB”) plans | 2025: 579
> Changes related to AOCI applicable to capital > Changes related to other CET1 capital adjustments | 2025: (2,114)
> Changes related to AOCI applicable to capital > Change in Standardized/Advanced CET1 capital | 2025: 12,956
> Changes related to AOCI applicable to capital > Standardized/Advanced CET1 capital at December 31, 2025 | 2025: $288,469
> Changes related to AOCI applicable to capital > Standardized/Advanced Tier 1 capital at December 31, 2024 | 2025: $294,881
> Changes related to AOCI applicable to capital > Change in CET1 capital | 2025: 12,956
> Changes related to AOCI applicable to capital > Net redemptions of noncumulative perpetual preferred stock | 2025: (5)
> Changes related to AOCI applicable to capital > Other | 2025: (202)
> Changes related to AOCI applicable to capital > Change in Standardized/Advanced Tier 1 capital | 2025: 12,749
> Changes related to AOCI applicable to capital > Standardized/Advanced Tier 1 capital at December 31, 2025 | 2025: $307,630

</details>

---

<!-- item: T10 judge: faithful -->
## 14. T10: What was Johnson & Johnson's research and development expense in 2025?

**Answer**

> Johnson & Johnson’s total research and development expense for fiscal year 2025 was **$14,665 million**[1].

**Judge verdict: faithful.** The answer correctly states the total research and development expense for 2025 as $14,665 million, which is explicitly listed in passage [1].

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] ★ Johnson & Johnson 10-K FY2025 — Item 7. Management’s discussion and analysis of results of operations and financial condition (p. 35)**

> Table: Research and development expense by segment of business was as follows:
> Units: Dollars in Millions
> Innovative Medicine | 2025 Amount: $11,827 | 2025 % of Sales*: 19.6% | 2024 Amount: $13,529 | 2024 % of Sales*: 23.8%
> MedTech | 2025 Amount: 2,838 | 2025 % of Sales*: 8.4 | 2024 Amount: 3,703 | 2024 % of Sales*: 11.6
> Total research and development expense | 2025 Amount: $14,665 | 2025 % of Sales*: 15.6% | 2024 Amount: $17,232 | 2024 % of Sales*: 19.4%
> Percent increase/(decrease) over the prior year | 2025 Amount: (14.9%) | 2024 Amount: 14.2%

**[2] Johnson & Johnson 10-K FY2024 — Item 7. Management’s discussion and analysis of results of operations and financial condition (p. 35)**

> Table: Research and development expense by segment of business was as follows:
> Units: Dollars in Millions
> Innovative Medicine | 2024 Amount: $13,529 | 2024 % of Sales*: 23.8% | 2023 Amount: $11,963 | 2023 % of Sales*: 21.8%
> MedTech | 2024 Amount: 3,703 | 2024 % of Sales*: 11.6 | 2023 Amount: 3,122 | 2023 % of Sales*: 10.3
> Total research and development expense | 2024 Amount: $17,232 | 2024 % of Sales*: 19.4% | 2023 Amount: $15,085 | 2023 % of Sales*: 17.7%
> Percent increase/(decrease) over the prior year | 2024 Amount: 14.2% | 2023 Amount: 6.7%

**[3] Johnson & Johnson 10-K FY2023 — Item 7. Management’s discussion and analysis of results of operations and financial condition (p. 35)**

> Table: Research and development expense by segment of business was as follows:
> Units: Dollars in Millions
> Innovative Medicine | 2023 Amount: $11,963 | 2023 % of Sales*: 21.8% | 2022 Amount: $11,642 | 2022 % of Sales*: 22.1%
> MedTech | 2023 Amount: 3,122 | 2023 % of Sales*: 10.3 | 2022 Amount: 2,493 | 2022 % of Sales*: 9.1
> Total research and development expense | 2023 Amount: $15,085 | 2023 % of Sales*: 17.7% | 2022 Amount: $14,135 | 2022 % of Sales*: 17.7%
> Percent increase/(decrease) over the prior year | 2023 Amount: 6.7% | 2022 Amount: (1.0%)

**[4] Johnson & Johnson 10-K FY2025 — Item 7. Management’s discussion and analysis of results of operations and financial condition (pp. 35–36)**

> Research and development activities represent a significant part of the Company's business. These expenditures relate to the processes of discovering, testing and developing new products, upfront payments and developmental milestones, improving existing products, as well as ensuring product efficacy and regulatory compliance prior to launch. The Company remains committed to investing in research and development with the aim of delivering high quality and innovative products.
>
> Research and Development decreased as a percent to sales primarily driven by:
>
> •Acquired in-process research & development expense of $1.25 billion to secure the global rights to the NM26 bispecific antibody (Yellow Jersey acquisition) in the Innovative Medicine business in 2024
>
> •Acquired in-process research & development expense of $0.5 billion from the V-Wave acquisition and a Laminar milestone of $0.3 billion in the MedTech business in 2024
>
> •Leverage resulting from investment prioritization in the Innovative Medicine business
>
> In-Process Research and Development Impairments (IPR&D): In the fiscal year 2025, the Company recorded a charge of approximately $0.1 billion primarily related to a non-strategic asset acquired with Abiomed in 2022. In the fiscal year 2024, the Company recorded a charge of approximately $0.2 billion primarily associated with the M710 (biosimilar) asset acquired as part of the acquisition of Momenta Pharmaceuticals in 2020. There was also a partial impairment of this asset for $0.2 billion in the fiscal 2023. This asset is fully impaired.
>
> Other (Income) Expense, Net: Other (income) expense, net is the account where the Company records gains and losses related to the sale and write-down of certain investments in equity securities held by Johnson & Johnson Innovation - JJDC, Inc. (JJDC), changes in the fair value of securities, investment (income)/loss related to employee benefit programs, gains and losses on divestitures, certain transactional currency gains and losses, acquisition and divestiture related costs, litigation accruals and settlements, as well as royalty income.
>
> Other (income) expense, net for the fiscal year 2025 reflected an increase in income of $11.9 billion as compared to the prior year primarily due to the following:

**[5] Johnson & Johnson 10-K FY2025 — Item 8. Financial statements and supplementary data (pp. 58–59)**

> Research and development payments to collaborative partner | Research and development expense
>
> Research and development payments received from collaborative partner or government entity | Reduction of Research and development expense
>
> * Milestones are capitalized as intangible assets and amortized to cost of products sold over the useful life.
>
> For all years presented, there was no individual project that represented greater than 5% of the total annual consolidated research and development expense other than the acquired in-process research & development expense of $1.25 billion to secure the global rights to the NM26 bispecific antibody (Yellow Jersey acquisition) in fiscal year 2024.
>
> The Company has a number of products and compounds developed in collaboration with strategic partners including XARELTO, co-developed with Bayer HealthCare AG, IMBRUVICA, developed in collaboration and co-marketed with Pharmacyclics LLC, an AbbVie company and CARVYKTI, licensed and developed in collaboration with Legend Biotech USA Inc. and Legend Biotech Ireland Limited.
>
> Separately, the Company has a number of licensing arrangements for products and compounds including DARZALEX, licensed from Genmab A/S.
>
> Advertising
>
> Costs associated with advertising are expensed in the year incurred and are included in selling, marketing and administrative expenses. Advertising expenses worldwide, which comprised television, radio, print media and Internet advertising, were $1.6 billion, $0.6 billion and $0.5 billion in fiscal years 2025, 2024 and 2023, respectively.
>
> Income taxes
>
> Income taxes are recorded based on amounts refundable or payable for the current year and include the results of any difference between U.S. GAAP accounting and tax reporting, recorded as deferred tax assets or liabilities. The Company estimates deferred tax assets and liabilities based on enacted tax law and rates. Future changes in tax laws and rates may affect recorded deferred tax assets and liabilities in the future.
>
> The Company records unrecognized tax benefits for uncertain tax positions. The Company follows U.S. GAAP which prescribes a recognition threshold and measurement attribute for the financial statement recognition and measurement of a tax position taken or expected to be taken in a tax return. Management believes that changes in these estimates would not have a material effect on the Company's results of operations, cash flows or financial position.

**[6] Johnson & Johnson 10-K FY2024 — Item 7. Management’s discussion and analysis of results of operations and financial condition (pp. 35–36)**

> Research and development activities represent a significant part of the Company's business. These expenditures relate to the processes of discovering, testing and developing new products, upfront payments and developmental milestones, improving existing products, as well as ensuring product efficacy and regulatory compliance prior to launch. The Company remains committed to investing in research and development with the aim of delivering high quality and innovative products.
>
> Research and Development increased as a percent to sales primarily driven by:
>
> •Acquired in-process research & development expense of $1.25 billion to secure the global rights to the NM26 bispecific antibody (Yellow Jersey acquisition) and pipeline advancement in the Innovative Medicine business
>
> •Acquired in-process research & development expense of $0.5 billion from the V-Wave acquisition in the MedTech business
>
> In-Process Research and Development Impairments (IPR&D): In the fiscal year 2024, the Company recorded a charge of approximately $0.2 billion associated with the M710 (biosimilar) asset acquired as part of the acquisition of Momenta Pharmaceuticals in 2020. There was also a partial impairment of this asset for $0.2 billion in the fiscal 2023. This asset is now fully impaired.
>
> Other (Income) Expense, Net: Other (income) expense, net is the account where the Company records gains and losses related to the sale and write-down of certain investments in equity securities held by Johnson & Johnson Innovation - JJDC, Inc. (JJDC), changes in the fair value of securities, investment (income)/loss related to employee benefit programs, gains and losses on divestitures, certain transactional currency gains and losses, acquisition and divestiture related costs, litigation accruals and settlements, as well as royalty income.
>
> Other (income) expense, net for the fiscal year 2024 reflected less expense of $1.9 billion as compared to the prior year primarily due to the following:

</details>

---

<!-- item: T12 judge: faithful -->
## 15. T12: What were Apple's diluted earnings per share in fiscal 2026?

**Answer**

> Apple’s diluted earnings per share for fiscal 2026 were **$8.98** per share[1†L9-L10][6†L7-L8].

**Judge verdict: faithful.** The answer correctly states that Apple's diluted earnings per share for fiscal 2026 were $8.98, which is explicitly supported by passages [1] and [6].

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] ★ Apple Inc. 10-K FY2026 — Item 8. Financial Statements and Supplementary Data (p. 41)**

> Table: The following table shows the computation of basic and diluted earnings per share for 2026, 2025 and 2024 (net income in millions and shares in thousands):
> Units: in millions
> Numerator > Net income | 2026: $132,175 | 2025: $112,010 | 2024: $93,736
> Denominator > Weighted-average basic shares outstanding | 2026: 14,661,935 | 2025: 14,948,500 | 2024: 15,343,783
> Denominator > Effect of dilutive share-based awards | 2026: 58,371 | 2025: 56,197 | 2024: 64,312
> Denominator > Weighted-average diluted shares | 2026: 14,720,306 | 2025: 15,004,697 | 2024: 15,408,095
> Denominator > Basic earnings per share | 2026: $9.01 | 2025: $7.49 | 2024: $6.11
> Denominator > Diluted earnings per share | 2026: $8.98 | 2025: $7.46 | 2024: $6.08

**[2] Apple Inc. 10-K FY2025 — Item 8. Financial Statements and Supplementary Data (p. 38)**

> Table: The following table shows the computation of basic and diluted earnings per share for 2025, 2024 and 2023 (net income in millions and shares in thousands):
> Units: in millions
> Numerator > Net income | 2025: $112,010 | 2024: $93,736 | 2023: $96,995
> Denominator > Weighted-average basic shares outstanding | 2025: 14,948,500 | 2024: 15,343,783 | 2023: 15,744,231
> Denominator > Effect of dilutive share-based awards | 2025: 56,197 | 2024: 64,312 | 2023: 68,316
> Denominator > Weighted-average diluted shares | 2025: 15,004,697 | 2024: 15,408,095 | 2023: 15,812,547
> Denominator > Basic earnings per share | 2025: $7.49 | 2024: $6.11 | 2023: $6.16
> Denominator > Diluted earnings per share | 2025: $7.46 | 2024: $6.08 | 2023: $6.13

**[3] Apple Inc. 10-K FY2024 — Item 8. Financial Statements and Supplementary Data (p. 38)**

> Table: The following table shows the computation of basic and diluted earnings per share for 2024, 2023 and 2022 (net income in millions and shares in thousands):
> Units: in millions
> Numerator > Net income | 2024: $93,736 | 2023: $96,995 | 2022: $99,803
> Denominator > Weighted-average basic shares outstanding | 2024: 15,343,783 | 2023: 15,744,231 | 2022: 16,215,963
> Denominator > Effect of dilutive share-based awards | 2024: 64,312 | 2023: 68,316 | 2022: 109,856
> Denominator > Weighted-average diluted shares | 2024: 15,408,095 | 2023: 15,812,547 | 2022: 16,325,819
> Denominator > Basic earnings per share | 2024: $6.11 | 2023: $6.16 | 2022: $6.15
> Denominator > Diluted earnings per share | 2024: $6.08 | 2023: $6.13 | 2022: $6.11

**[4] Apple Inc. 10-K FY2024 — Item 8. Financial Statements and Supplementary Data (pp. 37–38)**

> (1)Services net sales include amortization of the deferred value of services bundled in the sales price of certain products.
>
> Total net sales include $7.7 billion of revenue recognized in 2024 that was included in deferred revenue as of September 30, 2023, $8.2 billion of revenue recognized in 2023 that was included in deferred revenue as of September 24, 2022, and $7.5 billion of revenue recognized in 2022 that was included in deferred revenue as of September 25, 2021.
>
> The Company’s proportion of net sales by disaggregated revenue source was generally consistent for each reportable segment in Note 13, “Segment Information and Geographic Data” for 2024, 2023 and 2022, except in Greater China, where iPhone revenue represented a moderately higher proportion of net sales.
>
> As of September 28, 2024 and September 30, 2023, the Company had total deferred revenue of $12.8 billion and $12.1 billion, respectively. As of September 28, 2024, the Company expects 64% of total deferred revenue to be realized in less than a year, 25% within one-to-two years, 9% within two-to-three years and 2% in greater than three years.
>
> Note 3 – Earnings Per Share
>
> The following table shows the computation of basic and diluted earnings per share for 2024, 2023 and 2022 (net income in millions and shares in thousands):

**[5] Apple Inc. 10-K FY2025 — Item 8. Financial Statements and Supplementary Data (p. 31)**

> Table: (In millions, except number of shares, which are reflected in thousands, and per-share amounts)
> Units: In millions, except number of shares, which are reflected in thousands, and per-share amounts
> Operating income | Years ended September 27, 2025: 133,050 | Years ended September 28, 2024: 123,216 | Years ended September 30, 2023: 114,301
> Other income/(expense), net | Years ended September 27, 2025: (321) | Years ended September 28, 2024: 269 | Years ended September 30, 2023: (565)
> Income before provision for income taxes | Years ended September 27, 2025: 132,729 | Years ended September 28, 2024: 123,485 | Years ended September 30, 2023: 113,736
> Provision for income taxes | Years ended September 27, 2025: 20,719 | Years ended September 28, 2024: 29,749 | Years ended September 30, 2023: 16,741
> Net income | Years ended September 27, 2025: $112,010 | Years ended September 28, 2024: $93,736 | Years ended September 30, 2023: $96,995
> Earnings per share > Basic | Years ended September 27, 2025: $7.49 | Years ended September 28, 2024: $6.11 | Years ended September 30, 2023: $6.16
> Earnings per share > Diluted | Years ended September 27, 2025: $7.46 | Years ended September 28, 2024: $6.08 | Years ended September 30, 2023: $6.13
> Shares used in computing earnings per share > Basic | Years ended September 27, 2025: 14,948,500 | Years ended September 28, 2024: 15,343,783 | Years ended September 30, 2023: 15,744,231
> Shares used in computing earnings per share > Diluted | Years ended September 27, 2025: 15,004,697 | Years ended September 28, 2024: 15,408,095 | Years ended September 30, 2023: 15,812,547

**[6] ★ Apple Inc. 10-K FY2026 — Item 8. Financial Statements and Supplementary Data (p. 34)**

> Table: (In millions, except number of shares, which are reflected in thousands, and per-share amounts)
> Units: In millions, except number of shares, which are reflected in thousands, and per-share amounts
> Operating expenses > Total operating expenses | Years Ended September 26, 2026: 75,539 | Years Ended September 27, 2025: 62,151 | Years Ended September 28, 2024: 57,467
> Operating income | Years Ended September 26, 2026: 158,063 | Years Ended September 27, 2025: 133,050 | Years Ended September 28, 2024: 123,216
> Other income/(expense), net | Years Ended September 26, 2026: 1,174 | Years Ended September 27, 2025: (321) | Years Ended September 28, 2024: 269
> Income before provision for income taxes | Years Ended September 26, 2026: 159,237 | Years Ended September 27, 2025: 132,729 | Years Ended September 28, 2024: 123,485
> Provision for income taxes | Years Ended September 26, 2026: 27,062 | Years Ended September 27, 2025: 20,719 | Years Ended September 28, 2024: 29,749
> Net income | Years Ended September 26, 2026: $132,175 | Years Ended September 27, 2025: $112,010 | Years Ended September 28, 2024: $93,736
> Earnings per share > Basic | Years Ended September 26, 2026: $9.01 | Years Ended September 27, 2025: $7.49 | Years Ended September 28, 2024: $6.11
> Earnings per share > Diluted | Years Ended September 26, 2026: $8.98 | Years Ended September 27, 2025: $7.46 | Years Ended September 28, 2024: $6.08
> Shares used in computing earnings per share > Basic | Years Ended September 26, 2026: 14,661,935 | Years Ended September 27, 2025: 14,948,500 | Years Ended September 28, 2024: 15,343,783

</details>

---

<!-- item: Y01 judge: faithful -->
## 16. Y01: How did Apple's total net sales change from fiscal 2025 to fiscal 2026?

**Answer**

> Apple’s total net sales rose from $416,161 million in fiscal 2025 to $478,834 million in fiscal 2026, an increase of $62,673 million, or 15 % [5].

**Judge verdict: faithful.** The answer correctly cites the total net sales figures for fiscal 2025 ($416,161 million) and fiscal 2026 ($478,834 million) from passage [5], and the calculated difference ($62,673 million) and percentage increase (15%) are supported by the data and explicit change column in that passage.

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] Apple Inc. 10-K FY2026 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 28–29)**

> (1)Services net sales include amortization of the deferred value of services bundled in the sales price of certain products.
>
> iPhone
>
> iPhone net sales increased during 2026 compared to 2025 due to higher net sales of Pro models.
>
> Mac
>
> Mac net sales increased during 2026 compared to 2025 due to higher net sales of laptops.
>
> iPad
>
> iPad net sales during 2026 compared to 2025 were relatively flat.
>
> Wearables, Home and Accessories
>
> Wearables, Home and Accessories net sales during 2026 compared to 2025 were relatively flat.
>
> Services
>
> Services net sales increased during 2026 compared to 2025 primarily due to higher net sales from advertising and cloud services.
>
> Gross Margin
>
> Products and Services gross margin and gross margin percentage for 2026, 2025 and 2024 were as follows (dollars in millions):

**[2] Apple Inc. 10-K FY2025 — Item 8. Financial Statements and Supplementary Data (p. 38)**

> (1)Services net sales include amortization of the deferred value of services bundled in the sales price of certain products.
>
> The Company’s proportion of net sales by disaggregated revenue source was generally consistent for each reportable segment in Note 13, “Segment Information and Geographic Data” for 2025, 2024 and 2023, except in Greater China, where iPhone revenue represented a moderately higher proportion of net sales.
>
> As of September 27, 2025 and September 28, 2024, the Company had total deferred revenue of $13.7 billion and $12.8 billion, respectively. As of September 27, 2025, the Company expects 66% of total deferred revenue to be realized in less than a year, 23% within one-to-two years, 9% within two-to-three years and 2% in greater than three years.
>
> Note 3 – Earnings Per Share
>
> The following table shows the computation of basic and diluted earnings per share for 2025, 2024 and 2023 (net income in millions and shares in thousands):

**[3] Apple Inc. 10-K FY2026 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 27–28)**

> Americas
>
> Americas net sales increased during 2026 compared to 2025 due to higher net sales of iPhone, Services and Mac.
>
> Europe
>
> Europe net sales increased during 2026 compared to 2025 primarily due to higher net sales of iPhone, Services and Mac. The strength in foreign currencies relative to the U.S. dollar had a net favorable year-over-year impact on Europe net sales during 2026.
>
> Greater China
>
> Greater China net sales increased during 2026 compared to 2025 primarily due to higher net sales of iPhone and Mac. The strength in the renminbi relative to the U.S. dollar had a favorable year-over-year impact on Greater China net sales during 2026.
>
> Japan
>
> Japan net sales increased during 2026 compared to 2025 due to higher net sales of iPhone. The weakness in the yen relative to the U.S. dollar had an unfavorable year-over-year impact on Japan net sales during 2026.
>
> Rest of Asia Pacific
>
> Rest of Asia Pacific net sales increased during 2026 compared to 2025 primarily due to higher net sales of iPhone, Services and Mac.
>
> Products and Services Performance
>
> The following table shows net sales by category for 2026, 2025 and 2024 (dollars in millions):

**[4] Apple Inc. 10-K FY2026 — Item 8. Financial Statements and Supplementary Data (p. 55)**

> Table: The following tables show net sales for 2026, 2025 and 2024 and long-lived assets as of September 26, 2026 and September 27, 2025 for countries that individually accounted for 10% or more of the respective totals, as well as aggregate amounts for the
> Net sales > U.S. | 2026: $167,746 | 2025: $151,790 | 2024: $142,196
> Net sales > China (1) | 2026: 82,378 | 2025: 64,377 | 2024: 66,952
> Net sales > Other countries | 2026: 228,710 | 2025: 199,994 | 2024: 181,887
> Net sales > Total net sales | 2026: $478,834 | 2025: $416,161 | 2024: $391,035

**[5] ★ Apple Inc. 10-K FY2026 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 28)**

> Table: The following table shows net sales by category for 2026, 2025 and 2024 (dollars in millions):
> Units: dollars in millions
> iPhone | 2026: $254,098 | Change: 21% | 2025: $209,586 | Change: 4% | 2024: $201,183
> Mac | 2026: 37,929 | Change: 13% | 2025: 33,708 | Change: 12% | 2024: 29,984
> iPad | 2026: 27,929 | Change: —% | 2025: 28,023 | Change: 5% | 2024: 26,694
> Wearables, Home and Accessories | 2026: 35,577 | Change: —% | 2025: 35,686 | Change: (4)% | 2024: 37,005
> Services (1) | 2026: 123,301 | Change: 13% | 2025: 109,158 | Change: 14% | 2024: 96,169
> Total net sales | 2026: $478,834 | Change: 15% | 2025: $416,161 | Change: 6% | 2024: $391,035

**[6] Apple Inc. 10-K FY2025 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 25–26)**

> (1)Services net sales include amortization of the deferred value of services bundled in the sales price of certain products.
>
> iPhone
>
> iPhone net sales increased during 2025 compared to 2024 due to higher net sales of Pro models.
>
> Mac
>
> Mac net sales increased during 2025 compared to 2024 primarily due to higher net sales of laptops and desktops.
>
> iPad
>
> iPad net sales increased during 2025 compared to 2024 primarily due to higher net sales of iPad Air, iPad mini and iPad, partially offset by lower net sales of iPad Pro.
>
> Wearables, Home and Accessories
>
> Wearables, Home and Accessories net sales decreased during 2025 compared to 2024 primarily due to lower net sales of Accessories and Wearables.
>
> Services
>
> Services net sales increased during 2025 compared to 2024 primarily due to higher net sales from advertising, the App Store and cloud services.
>
> Gross Margin
>
> Products and Services gross margin and gross margin percentage for 2025, 2024 and 2023 were as follows (dollars in millions):

</details>

---

<!-- item: Y03 judge: faithful -->
## 17. Y03: How did AWS net sales change from 2024 to 2025?

**Answer**

> AWS net sales rose from $107,556 million in 2024 to $128,725 million in 2025, an increase of $21,169 million [5].

**Judge verdict: faithful.** The answer correctly cites the AWS net sales figures for 2024 ($107,556 million) and 2025 ($128,725 million) from passage [5] and correctly calculates the difference ($21,169 million).

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] Amazon.com, Inc. 10-K FY2024 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 24–25)**

> Sales increased 11% in 2024, compared to the prior year. Changes in foreign exchange rates reduced net sales by $2.3 billion in 2024. For a discussion of the effect of foreign exchange rates on sales growth, see “Effect of Foreign Exchange Rates” below.
>
> North America sales increased 10% in 2024, compared to the prior year. The sales growth primarily reflects increased unit sales, including sales by third-party sellers, advertising sales, and subscription services. Increased unit sales were driven largely by our continued focus on price, selection, and convenience for our customers, including from our fast shipping offers. Changes in foreign exchange rates reduced North America net sales by $462 million in 2024.
>
> International sales increased 9% in 2024, compared to the prior year. The sales growth primarily reflects increased unit sales, including sales by third-party sellers, advertising sales, and subscription services. Increased unit sales were driven largely by our continued focus on price, selection, and convenience for our customers, including from our fast shipping offers. Changes in foreign exchange rates reduced International net sales by $1.8 billion in 2024.
>
> AWS sales increased 19% in 2024, compared to the prior year. The sales growth primarily reflects increased customer usage, partially offset by pricing changes primarily driven by long-term customer contracts.
>
> Operating Expenses
>
> Information about operating expenses is as follows (in millions):

**[2] Amazon.com, Inc. 10-K FY2025 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 24–25)**

> Sales increased 12% in 2025, compared to the prior year. Changes in foreign exchange rates increased net sales by $4.4 billion in 2025. For a discussion of the effect of foreign exchange rates on sales growth, see “Effect of Foreign Exchange Rates” below.
>
> North America sales increased 10% in 2025, compared to the prior year. The sales growth primarily reflects increased unit sales, including sales by third-party sellers, advertising sales, and subscription services. Increased unit sales were driven largely by our continued focus on price, selection, and convenience for our customers, including from our fast shipping offers. Changes in foreign exchange rates reduced North America net sales by $454 million in 2025.
>
> International sales increased 13% in 2025, compared to the prior year. The sales growth primarily reflects increased unit sales, including sales by third-party sellers, advertising sales, and subscription services. Increased unit sales were driven largely
>
> by our continued focus on price, selection, and convenience for our customers, including from our fast shipping offers. Changes in foreign exchange rates increased International net sales by $4.9 billion in 2025.
>
> AWS sales increased 20% in 2025, compared to the prior year. The sales growth primarily reflects increased customer usage, partially offset by pricing changes primarily driven by long-term customer contracts.
>
> Operating Expenses
>
> Information about operating expenses is as follows (in millions):

**[3] Amazon.com, Inc. 10-K FY2023 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 24–25)**

> Sales increased 12% in 2023, compared to the prior year. Changes in foreign exchange rates reduced net sales by $71 million in 2023. For a discussion of the effect of foreign exchange rates on sales growth, see “Effect of Foreign Exchange Rates” below.
>
> North America sales increased 12% in 2023, compared to the prior year. The sales growth primarily reflects increased unit sales, primarily by third-party sellers, advertising sales, and subscription services. Increased unit sales were driven largely by our continued focus on price, selection, and convenience for our customers, including from our shipping offers.
>
> International sales increased 11% in 2023, compared to the prior year. The sales growth primarily reflects increased unit sales, primarily by third-party sellers, advertising sales, and subscription services. Increased unit sales were driven largely by our continued focus on price, selection, and convenience for our customers, including from our shipping offers. Changes in foreign exchange rates increased International net sales by $88 million in 2023.
>
> AWS sales increased 13% in 2023, compared to the prior year. The sales growth primarily reflects increased customer usage, partially offset by pricing changes, primarily driven by long-term customer contracts.
>
> Operating Income (Loss)
>
> Operating income (loss) by segment is as follows (in millions):

**[4] Amazon.com, Inc. 10-K FY2023 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 24)**

> We also expect the current macroeconomic environment and enterprise customer cost optimization efforts to impact our AWS revenue growth rates. We expect some or all of these factors to continue to impact our operations into Q1 2024.
>
> Net Sales
>
> Net sales include product and service sales. Product sales represent revenue from the sale of products and related shipping fees and digital media content where we record revenue gross. Service sales primarily represent third-party seller fees, which includes commissions and any related fulfillment and shipping fees, AWS sales, advertising services, Amazon Prime membership fees, and certain digital media content subscriptions. Net sales information is as follows (in millions):

**[5] ★ Amazon.com, Inc. 10-K FY2025 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 24)**

> Table: Net sales include product and service sales. Product sales represent revenue from the sale of products and related shipping fees and digital media content where we record revenue gross. Service sales primarily represent third-party seller fees, which
> Net Sales > North America | Year Ended December 31, 2024: $387,497 | Year Ended December 31, 2025: $426,305
> Net Sales > International | Year Ended December 31, 2024: 142,906 | Year Ended December 31, 2025: 161,894
> Net Sales > AWS | Year Ended December 31, 2024: 107,556 | Year Ended December 31, 2025: 128,725
> Net Sales > Consolidated | Year Ended December 31, 2024: $637,959 | Year Ended December 31, 2025: $716,924
> Year-over-year Percentage Growth > North America | Year Ended December 31, 2024: 10% | Year Ended December 31, 2025: 10%
> Year-over-year Percentage Growth > International | Year Ended December 31, 2024: 9 | Year Ended December 31, 2025: 13
> Year-over-year Percentage Growth > AWS | Year Ended December 31, 2024: 19 | Year Ended December 31, 2025: 20
> Year-over-year Percentage Growth > Consolidated | Year Ended December 31, 2024: 11 | Year Ended December 31, 2025: 12
> Year-over-year Percentage Growth, excluding the effect of foreign exchange rates > North America | Year Ended December 31, 2024: 10% | Year Ended December 31, 2025: 10%
> Year-over-year Percentage Growth, excluding the effect of foreign exchange rates > International | Year Ended December 31, 2024: 10 | Year Ended December 31, 2025: 10
> Year-over-year Percentage Growth, excluding the effect of foreign exchange rates > AWS | Year Ended December 31, 2024: 19 | Year Ended December 31, 2025: 20
> Year-over-year Percentage Growth, excluding the effect of foreign exchange rates > Consolidated | Year Ended December 31, 2024: 11 | Year Ended December 31, 2025: 12

**[6] Amazon.com, Inc. 10-K FY2025 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 24)**

> Table: Net sales include product and service sales. Product sales represent revenue from the sale of products and related shipping fees and digital media content where we record revenue gross. Service sales primarily represent third-party seller fees, which
> Net Sales Mix > North America | Year Ended December 31, 2024: 61% | Year Ended December 31, 2025: 59%
> Net Sales Mix > International | Year Ended December 31, 2024: 22 | Year Ended December 31, 2025: 23
> Net Sales Mix > AWS | Year Ended December 31, 2024: 17 | Year Ended December 31, 2025: 18
> Net Sales Mix > Consolidated | Year Ended December 31, 2024: 100% | Year Ended December 31, 2025: 100%

</details>

---

<!-- item: Y05 judge: unfaithful -->
## 18. Y05: How did Johnson & Johnson's sales to customers change from 2024 to 2025?

**Answer**

> Johnson & Johnson’s sales to customers generally rose from 2024 to 2025 across most of its product segments:
>
> * **Surgery (Worldwide)** – up 3.0% [4]  
> * **Advanced (Worldwide)** – up 2.0% [4]  
> * **General (Worldwide)** – up 3.8% [4]  
> * **Vision (Worldwide)** – up 6.3% [3]  
> * **Contact lenses/Other (Worldwide)** – up 4.8% [3]  
> * **Hips (Worldwide)** – up 2.1% [5]  
> * **Knees (Worldwide)** – up 2.7% [5]  
> * **Trauma (U.S.)** – up 2.2% [5]  
> * **Neuroscience (Worldwide)** – up 10.1% [6]  
> * **Tremfya (Worldwide)** – up 40.5% [6]  
>
> Conversely, a few segments declined:
>
> * **Other Pulmonary Hypertension (Worldwide)** – down 12.7% [1]  
> * **Infectious Diseases (Worldwide)** – down 4.6% [1]  
> * **Advanced (International)** – down 6.6% [4]  
> * **General (Worldwide)** – down 0.2% [2] (though it rebounded in 2025)  
>
> Overall, the company’s 2025 sales to customers were higher than in 2024, with most major segments posting double‑digit or modest single‑digit growth, while a few smaller therapeutic areas experienced declines.

**Judge verdict: unfaithful.** The claim that General (Worldwide) sales declined by 0.2% in 2025 contradicts Passage [4], which states a 3.8% increase for 2025 vs 2024 (the 0.2% decline was for 2024 vs 2023), and the overall conclusion that total sales were higher is not supported by the provided passages which only list segment-level data.

Unsupported claims named by the judge:
- General (Worldwide) – down 0.2% [2] (though it rebounded in 2025)
- Overall, the company’s 2025 sales to customers were higher than in 2024

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] ★ Johnson & Johnson 10-K FY2025 — Item 8. Financial statements and supplementary data (p. 90)**

> Units: Dollars in Millions
> UPTRAVI > Worldwide | Sales to Customers 2025: 1,902 | Sales to Customers 2024: 1,817 | Sales to Customers 2023: 1,582 | % Change ’25 vs. ’24: 4.7 | % Change ’24 vs. ’23: 14.9
> OTHER PULMONARY HYPERTENSION > U.S. | Sales to Customers 2025: 54 | Sales to Customers 2024: 75 | Sales to Customers 2023: 79 | % Change ’25 vs. ’24: (27.0) | % Change ’24 vs. ’23: (5.1)
> OTHER PULMONARY HYPERTENSION > International | Sales to Customers 2025: 155 | Sales to Customers 2024: 165 | Sales to Customers 2023: 182 | % Change ’25 vs. ’24: (6.2) | % Change ’24 vs. ’23: (9.3)
> OTHER PULMONARY HYPERTENSION > Worldwide | Sales to Customers 2025: 209 | Sales to Customers 2024: 240 | Sales to Customers 2023: 260 | % Change ’25 vs. ’24: (12.7) | % Change ’24 vs. ’23: (7.7)
> Infectious Diseases > U.S. | Sales to Customers 2025: 1,264 | Sales to Customers 2024: 1,354 | Sales to Customers 2023: 1,500 | % Change ’25 vs. ’24: (6.6) | % Change ’24 vs. ’23: (9.8)
> Infectious Diseases > International | Sales to Customers 2025: 1,977 | Sales to Customers 2024: 2,042 | Sales to Customers 2023: 2,918 | % Change ’25 vs. ’24: (3.2) | % Change ’24 vs. ’23: (30.0)
> Infectious Diseases > Worldwide | Sales to Customers 2025: 3,241 | Sales to Customers 2024: 3,396 | Sales to Customers 2023: 4,418 | % Change ’25 vs. ’24: (4.6) | % Change ’24 vs. ’23: (23.1)

**[2] ★ Johnson & Johnson 10-K FY2024 — Item 8. Financial statements and supplementary data (p. 91)**

> Units: Dollars in Millions
> Surgery > Worldwide | Sales to Customers 2024: 9,845 | Sales to Customers 2023: 10,037 | Sales to Customers 2022: 9,690 | % Change ’24 vs. ’23: (1.9) | % Change ’23 vs. ’22: 3.6
> ADVANCED > U.S. | Sales to Customers 2024: 1,838 | Sales to Customers 2023: 1,833 | Sales to Customers 2022: 1,784 | % Change ’24 vs. ’23: 0.2 | % Change ’23 vs. ’22: 2.8
> ADVANCED > International | Sales to Customers 2024: 2,650 | Sales to Customers 2023: 2,837 | Sales to Customers 2022: 2,785 | % Change ’24 vs. ’23: (6.6) | % Change ’23 vs. ’22: 1.9
> ADVANCED > Worldwide | Sales to Customers 2024: 4,488 | Sales to Customers 2023: 4,671 | Sales to Customers 2022: 4,569 | % Change ’24 vs. ’23: (3.9) | % Change ’23 vs. ’22: 2.2
> GENERAL > U.S. | Sales to Customers 2024: 2,165 | Sales to Customers 2023: 2,198 | Sales to Customers 2022: 2,113 | % Change ’24 vs. ’23: (1.5) | % Change ’23 vs. ’22: 4.0
> GENERAL > International | Sales to Customers 2024: 3,192 | Sales to Customers 2023: 3,168 | Sales to Customers 2022: 3,008 | % Change ’24 vs. ’23: 0.8 | % Change ’23 vs. ’22: 5.3
> GENERAL > Worldwide | Sales to Customers 2024: 5,358 | Sales to Customers 2023: 5,366 | Sales to Customers 2022: 5,121 | % Change ’24 vs. ’23: (0.2) | % Change ’23 vs. ’22: 4.8

**[3] ★ Johnson & Johnson 10-K FY2025 — Item 8. Financial statements and supplementary data (p. 93)**

> Units: Dollars in Millions
> Vision > U.S. | Sales to Customers 2025: 2,225 | Sales to Customers 2024: 2,128 | Sales to Customers 2023: 2,086 | % Change ’25 vs. ’24: 4.6 | % Change ’24 vs. ’23: 2.0
> Vision > International | Sales to Customers 2025: 3,243 | Sales to Customers 2024: 3,018 | Sales to Customers 2023: 2,986 | % Change ’25 vs. ’24: 7.4 | % Change ’24 vs. ’23: 1.1
> Vision > Worldwide | Sales to Customers 2025: 5,468 | Sales to Customers 2024: 5,146 | Sales to Customers 2023: 5,072 | % Change ’25 vs. ’24: 6.3 | % Change ’24 vs. ’23: 1.5
> CONTACT LENSES / OTHER > U.S. | Sales to Customers 2025: 1,754 | Sales to Customers 2024: 1,684 | Sales to Customers 2023: 1,626 | % Change ’25 vs. ’24: 4.1 | % Change ’24 vs. ’23: 3.6
> CONTACT LENSES / OTHER > International | Sales to Customers 2025: 2,157 | Sales to Customers 2024: 2,049 | Sales to Customers 2023: 2,076 | % Change ’25 vs. ’24: 5.3 | % Change ’24 vs. ’23: (1.3)
> CONTACT LENSES / OTHER > Worldwide | Sales to Customers 2025: 3,910 | Sales to Customers 2024: 3,733 | Sales to Customers 2023: 3,702 | % Change ’25 vs. ’24: 4.8 | % Change ’24 vs. ’23: 0.8
> SURGICAL > U.S. | Sales to Customers 2025: 471 | Sales to Customers 2024: 444 | Sales to Customers 2023: 460 | % Change ’25 vs. ’24: 6.1 | % Change ’24 vs. ’23: (3.4)

**[4] ★ Johnson & Johnson 10-K FY2025 — Item 8. Financial statements and supplementary data (p. 92)**

> Units: Dollars in Millions
> Surgery > Worldwide | Sales to Customers 2025: 10,137 | Sales to Customers 2024: 9,845 | Sales to Customers 2023: 10,037 | % Change ’25 vs. ’24: 3.0 | % Change ’24 vs. ’23: (1.9)
> ADVANCED > U.S. | Sales to Customers 2025: 1,900 | Sales to Customers 2024: 1,838 | Sales to Customers 2023: 1,833 | % Change ’25 vs. ’24: 3.4 | % Change ’24 vs. ’23: 0.2
> ADVANCED > International | Sales to Customers 2025: 2,678 | Sales to Customers 2024: 2,650 | Sales to Customers 2023: 2,837 | % Change ’25 vs. ’24: 1.0 | % Change ’24 vs. ’23: (6.6)
> ADVANCED > Worldwide | Sales to Customers 2025: 4,577 | Sales to Customers 2024: 4,488 | Sales to Customers 2023: 4,671 | % Change ’25 vs. ’24: 2.0 | % Change ’24 vs. ’23: (3.9)
> GENERAL > U.S. | Sales to Customers 2025: 2,258 | Sales to Customers 2024: 2,165 | Sales to Customers 2023: 2,198 | % Change ’25 vs. ’24: 4.3 | % Change ’24 vs. ’23: (1.5)
> GENERAL > International | Sales to Customers 2025: 3,302 | Sales to Customers 2024: 3,192 | Sales to Customers 2023: 3,168 | % Change ’25 vs. ’24: 3.4 | % Change ’24 vs. ’23: 0.8
> GENERAL > Worldwide | Sales to Customers 2025: 5,560 | Sales to Customers 2024: 5,358 | Sales to Customers 2023: 5,366 | % Change ’25 vs. ’24: 3.8 | % Change ’24 vs. ’23: (0.2)

**[5] ★ Johnson & Johnson 10-K FY2025 — Item 8. Financial statements and supplementary data (p. 92)**

> Units: Dollars in Millions
> HIPS > U.S. | Sales to Customers 2025: 1,080 | Sales to Customers 2024: 1,057 | Sales to Customers 2023: 996 | % Change ’25 vs. ’24: 2.1 | % Change ’24 vs. ’23: 6.2
> HIPS > International | Sales to Customers 2025: 594 | Sales to Customers 2024: 581 | Sales to Customers 2023: 564 | % Change ’25 vs. ’24: 2.2 | % Change ’24 vs. ’23: 3.0
> HIPS > Worldwide | Sales to Customers 2025: 1,674 | Sales to Customers 2024: 1,638 | Sales to Customers 2023: 1,560 | % Change ’25 vs. ’24: 2.1 | % Change ’24 vs. ’23: 5.0
> KNEES > U.S. | Sales to Customers 2025: 924 | Sales to Customers 2024: 922 | Sales to Customers 2023: 896 | % Change ’25 vs. ’24: 0.2 | % Change ’24 vs. ’23: 2.9
> KNEES > International | Sales to Customers 2025: 663 | Sales to Customers 2024: 623 | Sales to Customers 2023: 559 | % Change ’25 vs. ’24: 6.5 | % Change ’24 vs. ’23: 11.3
> KNEES > Worldwide | Sales to Customers 2025: 1,587 | Sales to Customers 2024: 1,545 | Sales to Customers 2023: 1,456 | % Change ’25 vs. ’24: 2.7 | % Change ’24 vs. ’23: 6.1
> TRAUMA > U.S. | Sales to Customers 2025: 2,058 | Sales to Customers 2024: 2,013 | Sales to Customers 2023: 1,949 | % Change ’25 vs. ’24: 2.2 | % Change ’24 vs. ’23: 3.3

**[6] ★ Johnson & Johnson 10-K FY2025 — Item 8. Financial statements and supplementary data (p. 89)**

> Units: Dollars in Millions
> TREMFYA > Worldwide | Sales to Customers 2025: 5,155 | Sales to Customers 2024: 3,670 | Sales to Customers 2023: 3,147 | % Change ’25 vs. ’24: 40.5 | % Change ’24 vs. ’23: 16.6
> OTHER IMMUNOLOGY > U.S. | Sales to Customers 2025: 59 | Sales to Customers 2024: 3 | Sales to Customers 2023: 11 | % Change ’24 vs. ’23: (74.1)
> OTHER IMMUNOLOGY > International | Sales to Customers 2025: 2 | Sales to Customers 2024: 0 | Sales to Customers 2023: 0 | % Change ’24 vs. ’23: —
> OTHER IMMUNOLOGY > Worldwide | Sales to Customers 2025: 61 | Sales to Customers 2024: 3 | Sales to Customers 2023: 11 | % Change ’24 vs. ’23: (74.1)
> Neuroscience > U.S. | Sales to Customers 2025: 5,151 | Sales to Customers 2024: 4,398 | Sales to Customers 2023: 4,065 | % Change ’25 vs. ’24: 17.1 | % Change ’24 vs. ’23: 8.2
> Neuroscience > International | Sales to Customers 2025: 2,686 | Sales to Customers 2024: 2,718 | Sales to Customers 2023: 3,076 | % Change ’25 vs. ’24: (1.2) | % Change ’24 vs. ’23: (11.6)
> Neuroscience > Worldwide | Sales to Customers 2025: 7,837 | Sales to Customers 2024: 7,115 | Sales to Customers 2023: 7,140 | % Change ’25 vs. ’24: 10.1 | % Change ’24 vs. ’23: (0.4)
> CAPLYTA(3) > U.S. | Sales to Customers 2025: 700 | Sales to Customers 2024: — | Sales to Customers 2023: — | % Change ’24 vs. ’23: —

</details>

---

<!-- item: Y06 judge: faithful -->
## 19. Y06: By how much did Apple's research and development expense grow in fiscal 2026?

**Answer**

> Apple’s research and development expense increased by **$11,215 million** in fiscal 2026 (from $34,550 million in 2025 to $45,765 million in 2026)[2].

**Judge verdict: faithful.** The answer correctly calculates the difference between the 2026 and 2025 R&D expenses ($45,765 million - $34,550 million = $11,215 million) using the figures provided in passage [2].

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] Apple Inc. 10-K FY2024 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 26–27)**

> Research and Development
>
> The growth in R&D expense during 2024 compared to 2023 was driven primarily by increases in headcount-related expenses.
>
> Selling, General and Administrative
>
> Selling, general and administrative expense increased $1.2 billion during 2024 compared to 2023.
>
> Provision for Income Taxes
>
> Provision for income taxes, effective tax rate and statutory federal income tax rate for 2024, 2023 and 2022 were as follows (dollars in millions):

**[2] ★ Apple Inc. 10-K FY2026 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 29)**

> Table: Operating expenses for 2026, 2025 and 2024 were as follows (dollars in millions):
> Units: dollars in millions
> Research and development | 2026: $45,765 | Change: 32% | 2025: $34,550 | Change: 10% | 2024: $31,370
> Percentage of total net sales | 2026: 10% | 2025: 8% | 2024: 8%
> Selling, general and administrative | 2026: $29,774 | Change: 8% | 2025: $27,601 | Change: 6% | 2024: $26,097
> Percentage of total net sales | 2026: 6% | 2025: 7% | 2024: 7%
> Total operating expenses | 2026: $75,539 | Change: 22% | 2025: $62,151 | Change: 8% | 2024: $57,467
> Percentage of total net sales | 2026: 16% | 2025: 15% | 2024: 15%

**[3] Apple Inc. 10-K FY2026 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 29–30)**

> Research and Development
>
> R&D expense increased during 2026 compared to 2025 primarily due to higher infrastructure-related costs, including investments in artificial intelligence, and headcount-related expenses.
>
> Selling, General and Administrative
>
> Selling, general and administrative expense increased during 2026 compared to 2025. The increase was driven by various factors, none of which were significant individually or in the aggregate.
>
> Provision for Income Taxes
>
> Provision for income taxes and effective tax rate for 2026, 2025 and 2024 were as follows (dollars in millions):

**[4] Apple Inc. 10-K FY2024 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (p. 26)**

> Table: Operating expenses for 2024, 2023 and 2022 were as follows (dollars in millions):
> Units: dollars in millions
> Research and development | 2024: $31,370 | Change: 5% | 2023: $29,915 | Change: 14% | 2022: $26,251
> Percentage of total net sales | 2024: 8% | 2023: 8% | 2022: 7%
> Selling, general and administrative | 2024: $26,097 | Change: 5% | 2023: $24,932 | Change: (1)% | 2022: $25,094
> Percentage of total net sales | 2024: 7% | 2023: 7% | 2022: 6%
> Total operating expenses | 2024: $57,467 | Change: 5% | 2023: $54,847 | Change: 7% | 2022: $51,345
> Percentage of total net sales | 2024: 15% | 2023: 14% | 2022: 13%

**[5] Apple Inc. 10-K FY2025 — Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations (pp. 26–27)**

> Research and Development
>
> The growth in R&D expense during 2025 compared to 2024 was primarily driven by increases in headcount-related expenses and infrastructure-related costs.
>
> Selling, General and Administrative
>
> The growth in selling, general and administrative expense during 2025 compared to 2024 was primarily driven by increases in headcount-related expenses and variable selling expenses.
>
> Provision for Income Taxes
>
> Provision for income taxes, effective tax rate and statutory federal income tax rate for 2025, 2024 and 2023 were as follows (dollars in millions):

**[6] Apple Inc. 10-K FY2026 — Item 8. Financial Statements and Supplementary Data (p. 45)**

> Amortization expense related to intangible assets was $4.9 billion, $3.7 billion and $3.6 billion in 2026, 2025 and 2024, respectively. The expected annual amortization expense related to intangible assets as of September 26, 2026, is as follows (in millions):

</details>

---

<!-- item: Y07 judge: faithful -->
## 20. Y07: How did Microsoft Cloud revenue change between fiscal 2025 and fiscal 2026?

**Answer**

> Microsoft Cloud revenue grew from $168.9 billion in fiscal 2025 to $214.4 billion in fiscal 2026, an increase of $45.5 billion[6][4].

**Judge verdict: faithful.** The answer correctly cites the Microsoft Cloud revenue figures for fiscal 2025 ($168.9 billion) and fiscal 2026 ($214.4 billion) from passages [6] and [4], and the calculated difference of $45.5 billion is accurate.

**Your call**

- [x] Agree with the judge
- [ ] Disagree with the judge

Notes:

<details><summary>Passages the model saw (cited ones marked ★)</summary>

**[1] Microsoft Corporation 10-K FY2025 — Item 7. Management’s Discussion And Analysis Of Financial Condition And Results Of Operations (pp. 38–39)**

> Fiscal Year 2025 Compared with Fiscal Year 2024
>
> Revenue increased $36.6 billion or 15% with growth across each of our segments. Intelligent Cloud revenue increased driven by Azure. Productivity and Business Processes revenue increased driven by Microsoft 365 Commercial cloud. More Personal Computing revenue increased driven by Gaming and Search and news advertising.
>
> Cost of revenue increased $13.7 billion or 19% driven by growth in Microsoft Cloud.
>
> Gross margin increased $22.9 billion or 13% with growth across each of our segments.
>
> Gross margin percentage decreased slightly driven by Intelligent Cloud, offset in part by More Personal Computing.
>
> Microsoft Cloud gross margin percentage decreased to 69% driven by the impact of scaling our AI infrastructure, offset in part by efficiency gains in Azure.
>
> Operating expenses increased $3.8 billion or 6% driven by investments in cloud and AI engineering and Gaming, including the impact of the Activision Blizzard acquisition.
>
> Operating income increased $19.1 billion or 17% with growth across each of our segments.
>
> SEGMENT RESULTS OF OPERATIONS

**[2] Microsoft Corporation 10-K FY2026 — Item 7. Management’s Discussion And Analysis Of Financial Condition And Results Of Operations (pp. 38–39)**

> Reportable Segments
>
> Fiscal Year 2026 Compared with Fiscal Year 2025
>
> Productivity and Business Processes
>
> Revenue increased $19.2 billion or 16%.
>
> Microsoft 365 Commercial products and cloud services revenue increased $14.2 billion or 16%. Microsoft 365 Commercial cloud revenue grew 17% with growth in revenue per user driven by Microsoft 365 Copilot and Microsoft 365 E5. Microsoft 365 Commercial seats grew 6% driven by small and medium businesses and frontline worker offerings. Microsoft 365 Commercial products revenue grew 13% driven by growth in the Windows Commercial on-premises components of Microsoft 365 suite sales, as well as an increase in Office 2024 transactional purchasing.
>
> Microsoft 365 Consumer products and cloud services revenue increased $1.8 billion or 24%. Microsoft 365 Consumer cloud revenue grew 28% driven by growth in revenue per user and Microsoft 365 Consumer subscriber growth of 7%.
>
> LinkedIn revenue increased $2.0 billion or 11% with growth across all lines of business.
>
> Dynamics products and cloud services revenue increased $1.2 billion or 15% driven by growth in Dynamics 365. Dynamics 365 revenue grew 18% with growth across all workloads.
>
> Operating income increased $14.1 billion or 20%.
>
> Cost of revenue increased $2.6 billion or 12% driven by investments in AI infrastructure to support Microsoft 365 Copilot seat and usage growth.
>
> Gross margin increased $16.6 billion or 17% driven by growth in Microsoft 365 Commercial cloud. Gross margin percentage increased slightly primarily driven by efficiency gains in Microsoft 365 Commercial cloud, offset in part by continued investments in AI infrastructure and growing AI product usage.
>
> Operating expenses increased $2.5 billion or 9% driven by continued investments in research and development compute capacity, AI talent, and data to support product development that benefits the entire portfolio, as well as investments in commercial sales and higher Copilot advertising expenses.
>
> Revenue, gross margin, and operating income included a favorable foreign currency impact of 2%, 3%, and 3%, respectively.
>
> Intelligent Cloud
>
> Revenue increased $31.5 billion or 30%.
>
> Server products and cloud services revenue increased $31.0 billion or 31% driven by Azure and other cloud services. Azure and other cloud services revenue grew 41% driven by demand for services across the platform with continued growth across all workloads.

**[3] Microsoft Corporation 10-K FY2025 — Item 7. Management’s Discussion And Analysis Of Financial Condition And Results Of Operations (pp. 39–40)**

> Reportable Segments
>
> Fiscal Year 2025 Compared with Fiscal Year 2024
>
> Productivity and Business Processes
>
> Revenue increased $14.0 billion or 13%.
>
> Microsoft 365 Commercial products and cloud services revenue increased $10.8 billion or 14%. Microsoft 365 Commercial cloud revenue grew 15% with Microsoft 365 Commercial seat growth of 6% driven by small and medium businesses and frontline worker offerings, as well as growth in revenue per user. Microsoft 365 Commercial products revenue grew 7% driven by the Windows Commercial on-premises components of Microsoft 365 suite sales and an increase in Office transactional purchasing with the launch of Office 2024.
>
> Microsoft 365 Consumer products and cloud services revenue increased $756 million or 11%. Microsoft 365 Consumer cloud revenue grew 11% driven by Microsoft 365 Consumer subscriber growth of 8% to 89.0 million, as well as growth in revenue per user from the price increase announced in January 2025.
>
> LinkedIn revenue increased $1.4 billion or 9% with growth across all lines of business.
>
> Dynamics products and cloud services revenue increased $996 million or 15% driven by growth in Dynamics 365, offset in part by a decline in Dynamics on-premises products. Dynamics 365 revenue grew 19% with growth across all workloads.
>
> Operating income increased $10.1 billion or 17%.
>
> Cost of revenue increased $2.8 billion or 14% driven by growth in Microsoft 365 Commercial cloud.
>
> Gross margin increased $11.2 billion or 13% driven by growth in Microsoft 365 Commercial cloud. Gross margin percentage decreased slightly primarily driven by the impact of scaling our AI infrastructure, offset in part by efficiency gains in Microsoft 365 Commercial cloud.
>
> Operating expenses increased $1.1 billion or 4% driven by investments in cloud and AI engineering and commercial sales.
>
> Intelligent Cloud
>
> Revenue increased $18.8 billion or 21%.
>
> Server products and cloud services revenue increased $18.6 billion or 23% driven by Azure and other cloud services. Azure and other cloud services revenue grew 34% driven by demand for our portfolio of services. Server products revenue decreased 3% driven by a decrease in transactional purchasing with continued customer shift to cloud offerings.
>
> Enterprise and partner services revenue increased $166 million or 2% driven by growth in Enterprise Support Services, offset in part by a decline in Industry Solutions.
>
> Operating income increased $6.8 billion or 18%.

**[4] ★ Microsoft Corporation 10-K FY2026 — Item 8. Financial Statements And Supplementary Data (p. 85)**

> Our Microsoft Cloud revenue, which includes Microsoft 365 Commercial cloud, Azure and other cloud services, the commercial portion of LinkedIn, and Dynamics 365, was $214.4 billion, $168.9 billion, and $137.7 billion in fiscal years 2026, 2025, and 2024, respectively. These amounts are included in Server products and cloud services, Microsoft 365 Commercial products and cloud services, LinkedIn, and Dynamics products and cloud services in the table above.
>
> Assets are not allocated to segments for internal reporting presentations. A portion of amortization and depreciation is included with various other costs in an overhead allocation to each segment. It is impracticable for us to separately identify the amount of amortization and depreciation by segment that is included in the measure of segment profit or loss.
>
> Long-lived assets, excluding financial instruments and tax assets, classified by the location of the controlling statutory company and with countries over 10% of the total shown separately, were as follows:

**[5] Microsoft Corporation 10-K FY2024 — Item 7. Management’s Discussion And Analysis Of Financial Condition And Results Of Operations (pp. 44–45)**

> Reportable Segments
>
> Fiscal Year 2024 Compared with Fiscal Year 2023
>
> Productivity and Business Processes
>
> Revenue increased $8.5 billion or 12%.
>
> Office Commercial products and cloud services revenue increased $5.8 billion or 14%. Office 365 Commercial revenue grew 16% with seat growth of 7%, driven by small and medium business and frontline worker offerings, as well as growth in revenue per user. Office Commercial products revenue declined 16% driven by continued customer shift to cloud offerings.
>
> Office Consumer products and cloud services revenue increased $237 million or 4%. Microsoft 365 Consumer subscribers grew 10% to 82.5 million.
>
> LinkedIn revenue increased $1.4 billion or 9% driven by growth across all lines of business – Talent Solutions, Premium Subscriptions, Marketing Solutions, and Sales Solutions.
>
> Dynamics products and cloud services revenue increased $1.0 billion or 19% driven by Dynamics 365. Dynamics 365 revenue grew 24% driven by growth across all workloads.
>
> Operating income increased $6.4 billion or 19%.
>
> Gross margin increased $6.5 billion or 12% driven by growth in Office 365 Commercial. Gross margin percentage decreased slightly. Excluding the impact of the change in accounting estimate, gross margin percentage increased slightly driven by improvement in Office 365 Commercial.
>
> Operating expenses increased $159 million or 1%.
>
> Intelligent Cloud
>
> Revenue increased $17.5 billion or 20%.
>
> Server products and cloud services revenue increased $17.8 billion or 22% driven by Azure and other cloud services. Azure and other cloud services revenue grew 30% driven by growth in our consumption-based services. Server products revenue increased 3% driven by continued demand for our hybrid solutions, including Windows Server and SQL Server running in multi-cloud environments.
>
> Enterprise and partner services revenue decreased $306 million or 4% driven by declines in Enterprise Support Services and Industry Solutions.
>
> Operating income increased $11.7 billion or 31%.
>
> Gross margin increased $11.6 billion or 19% driven by growth in Azure. Gross margin percentage decreased slightly. Excluding the impact of the change in accounting estimate, gross margin percentage increased slightly primarily driven by improvement in Azure, inclusive of scaling our AI infrastructure, offset in part by sales mix shift to Azure.
>
> Operating expenses decreased slightly primarily driven by the prior year Q2 charge, offset in part by investments in Azure.
>
> More Personal Computing
>
> Revenue increased $7.3 billion or 13%.

**[6] ★ Microsoft Corporation 10-K FY2025 — Item 8. Financial Statements And Supplementary Data (p. 85)**

> Our Microsoft Cloud revenue, which includes Microsoft 365 Commercial cloud, Azure and other cloud services, the commercial portion of LinkedIn, and Dynamics 365, was $168.9 billion, $137.7 billion, and $111.6 billion in fiscal years 2025, 2024, and 2023, respectively. These amounts are included in Microsoft 365 Commercial products and cloud services, Server products and cloud services, LinkedIn, and Dynamics products and cloud services in the table above.
>
> Assets are not allocated to segments for internal reporting presentations. A portion of amortization and depreciation is included with various other costs in an overhead allocation to each segment. It is impracticable for us to separately identify the amount of amortization and depreciation by segment that is included in the measure of segment profit or loss.
>
> Long-lived assets, excluding financial instruments and tax assets, classified by the location of the controlling statutory company and with countries over 10% of the total shown separately, were as follows:

</details>
