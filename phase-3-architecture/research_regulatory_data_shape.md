# Research — Regulatory / Settlement / Submission Data Shape (UA Electricity Market)

**Purpose:** define the SHAPE of submission, settlement, and regulatory data structures that GECKO VPP's synthetic dataset must reproduce so that a Ukrainian energy professional reads the demo as credible. This is "what goes into what field", not real datapoints.

**Frame:** v2 production-fidelity demo. We are not connecting to ОРЕЕ / Укренерго / ДП ГП APIs — but every table, file, and screen must look like it could.

**Scope:** ПРРОР (Правила Ринку), Кодекс системи передачі (КСП), Кодекс комерційного обліку (ККО), ENTSO-E codelists, КЕП wrapper, НКРЕКП публікація.

---

## 1. Forecast submission — Подача прогнозу виробництва / споживання

### Legal basis
- **Кодекс системи передачі** (постанова НКРЕКП № 309 від 14.03.2018, з поправками — найсвіжіша редакція з 01.01.2026 згідно постанови № 1462/2025). КСП §IV "Планування режимів роботи ОЕС України" регулює submission прогнозних графіків.
- **Правила ринку** (постанова НКРЕКП № 307 від 14.03.2018) §§3, 7 — обов'язки сторони, відповідальної за баланс (СВБ / BRP).
- **Кодекс комерційного обліку** (постанова НКРЕКП № 311 від 14.03.2018) — як заміри ув'язуються з прогнозом.

### Who submits what

| Role | What is submitted | Granularity |
|---|---|---|
| Виробник (producer, ≥ 1 МВт) | Прогнозний графік відпуску по кожному ресурсному об'єкту (`production schedule` / A01) | 60-min (історично); 15-min — заплановано в рамках узгодження з ENTSO-E MTU |
| Споживач C&I (≥ certain threshold) | Прогнозний графік споживання (A04) | 60-min |
| BRP (Сторона, відповідальна за баланс) | Агрегований графік по балансуючій групі | 60-min |
| Постачальник послуг балансування (BSP) | Декларація доступної потужності (A60 / A61 max-available) + activation bids на БР | 60-min, з intraday updates |

### Gate / deadline (D-1)
- **РДН gate closure:** historically 12:30 D-1 на ОРЕЕ; протягом 2023–2025 ОРЕЕ публікувала розклади з gate closure від 11:00 до 13:00 (для деяких сесій воєнного часу — extended до 13:00).
- **Прогноз для БР через Укренерго:** не пізніше gate closure РДН + до 14:00 D-1 (publication of merit order).
- **Intraday updates:** дозволені до H-1 (одна година до постачання) на ВДР.

### Format
- Через **Кабінет учасника ринку** (web portal) Укренерго / ОРЕЕ — основний канал.
- Машинно — **XML на основі ENTSO-E ESS / ESMP** (ENTSO-E Scheduling System / Electronic Scheduling Market Process), документ типу `ScheduleDocument` з business type A01/A04.
- Excel + ручне внесення припустиме для малих учасників; великі gencos і трейдери пишуть напряму через API кабінету.

### Поля одного рядка ряду (Period / Point)
Per ENTSO-E `ScheduleDocument.TimeSeries.Period.Point`:
- `timeInterval` (start/end ISO-8601, Europe/Kyiv → UTC)
- `resolution` (PT60M / PT15M)
- `position` (1..24 для часової доби; 1..96 для квартир-години)
- `quantity` (МВт·год; 3 знаки після коми)
- На рівні TimeSeries:
  - `mRID` (унікальний id ряду)
  - `businessType` (A01 production / A04 consumption / A85 internal)
  - `objectAggregation` (A03 area / A04 resource object)
  - `inBiddingZone_Domain.mRID` (EIC, наприклад 10Y1001C--00003F для UA BZN)
  - `meteringPoint_mRID` / `registeredResource.mRID` (EIC точки/ресурсу — 16 символів)
  - `measurementUnit.name` (MAW для megawatt-hours per resolution period)

### Recipient
- Прогноз generation/consumption → **НЕК Укренерго (ОСП)** як адміністратор комерційного обліку та оператор балансуючого ринку.
- Bids РДН/ВДР → **ОРЕЕ (ДП "Оператор ринку")**.
- Settlement зеленого тарифу → **ДП "Гарантований покупець"**.

Sources: <https://www.nerc.gov.ua/acts/pro-zatverdzhennya-kodeksu-sistemi-peredachi>, <https://ua.energy/uchasnikam_rinku/normatyvno-pravova-baza-funktsionuvannya-novoyi-modeli-rynku-elektroenergiyi-ukrayiny/struktura-kodeksu-systemy-peredachi/>, <https://www.oree.com.ua/>.

---

## 2. Bid to РДН (Day-Ahead Market)

### Structure
- Стандартний пакет — **24 hourly price-volume blocks** per delivery day (MTU = 60 min).
- Два типи заявок:
  - **Прості (simple / hourly)** — окреме price-volume per годину.
  - **Блокові (block bids)** — група послідовних годин, all-or-nothing, з мінімальним acceptance ratio. Доступні: regular block, profile block, linked block (як на EPEX / Nord Pool, в адаптованому вигляді на ОРЕЕ).
  - Step bids (multi-step price-volume curve per годину) — для крупних учасників.

### Поля однієї bid-row (hour granularity)
- `delivery_date` (DATE, доба постачання)
- `hour` (0..23, локальний час Києва, EET/EEST)
- `side` (BUY / SELL)
- `volume_mwh` (NUMERIC(10,3); крок 0.1 МВт·год)
- `price_uah_mwh` (NUMERIC(10,2); price floor / cap встановлюється ОРЕЕ — typically 1 to 9 000 грн/МВт·год)
- `bid_type` (SIMPLE / BLOCK / STEP)
- `block_id` (NULL для simple; UUID для всіх рядків одного блоку)
- `min_acceptance_ratio` (0.0..1.0; only block bids)
- `technology_type` (ENTSO-E PsrType, e.g. B01 biomass, B16 solar, B19 wind on-shore, B20 wind off-shore, B11 hydro RoR, B14 hydro pumped, B04 fossil gas)
- `participant_eic` (16-char EIC учасника, "X" prefix)
- `resource_eic` (16-char EIC ресурсного об'єкту, "W" prefix)
- `bid_id` (mRID унікальний)

### Submission gate
- Bid window opens at ~10:00 D-1, closes at gate-closure (history: 12:30 D-1; in 2024–2026 published gate 11:00–13:00 залежно від сесії).
- Aukcjon clearing single-side single-clearing-price близько 13:30–14:00 D-1.
- Confirmation back from ОРЕЕ: `MatchingResultDocument` із `acceptedQuantity`, `clearingPrice`, `status` (ACCEPTED / PARTIAL / REJECTED) — XML; також доступний в кабінеті.

Sources: <https://www.oree.com.ua/>, <https://www.gpee.com.ua/files/Постанова%20НКРЕКП%20від%2014.03.2018%20№%20307%20Правила%20ринку.pdf>.

---

## 3. Bid to ВДР (Intraday)

### Structure
- **Continuous matching** order book — pay-as-bid, FIFO time priority within price level. ОРЕЕ запустила continuous IDM в 2019, з 2024 синхронізація з SIDC (XBID) — поки на pilot рівні, до повної інтеграції IPS не дійшов через війну.
- Hourly products (та поступово 30-min, 15-min — coming на узгодженні з ENTSO-E).
- **Order types** на платформі ОРЕЕ:
  - **LIMIT** — основний.
  - **MARKET / immediate-or-cancel (IOC)** — обмежено.
  - **Fill-or-kill (FOK)** — для блоків.
  - **Iceberg** — для крупних учасників.
- Lead-time: ВДР відкривається після clearing РДН (~15:00 D-1) і закривається за 60 хвилин до постачання (H-1).
- Latency: matching engine event-driven, "real-time" (mid-seconds), publication по результатам — websocket / API push.

### Поля order
- `order_id` (UUID/mRID)
- `submitted_at` (TIMESTAMPTZ, ms precision)
- `delivery_start` / `delivery_end` (TIMESTAMPTZ)
- `side` (BUY / SELL)
- `volume_mwh`, `price_uah_mwh`
- `order_type` (LIMIT / MARKET / FOK / IOC / ICEBERG)
- `time_in_force` (GTD — good-till-date; GTC — good-till-cancel)
- `participant_eic`, `resource_eic`
- `state` (ACTIVE / FILLED / PARTIAL / CANCELLED / EXPIRED)
- `parent_order_id` (для iceberg children)

---

## 4. Settlement statement from ДП "Гарантований Покупець"

### Document name
**Акт прийому-передачі електричної енергії за "зеленим" тарифом** (бо ГП викуповує саме зелене виробництво). Окремо існує **Акт врегулювання небалансів** для БР через Укренерго.

### Період
- Місячний (calendar month). Виставляється до 5-го робочого дня місяця, що настає за розрахунковим.

### Поля
- Шапка:
  - `Договір №` / дата (типовий договір ГП per Постанова НКРЕКП № 641 від 26.04.2019)
  - Період (місяць/рік)
  - Реквізити сторін: ЄДРПОУ / ІПН, юр. адреса, банк, IBAN
- Тіло (per-asset breakdown):
  - № п/п, EIC точки обліку, назва об'єкта, тип ВДЕ (SPP / WPP / BIO / SHPP)
  - Обсяг по півгодинах (additional sheet — 30-min profile) → агрегат за місяць МВт·год
  - Зелений тариф (єврокоп./кВт·год або грн/кВт·год за курсом НБУ на 1-е число місяця)
  - Сума без ПДВ
  - **ПДВ:** операція з продажу електроенергії за зеленим тарифом виробником-юрособою — оподатковується **20 % ПДВ** (стандарт). 0 % застосовується тільки для експорту електроенергії або спеціальних режимів. Фіз-особи з СЕС до 50 кВт — не платники ПДВ.
  - Сума з ПДВ
- Підвал: підписи сторін (КЕП), штамп, дата формування.

### Формат
- Excel (.xlsx) для робочих обчислень + **PDF підписаний КЕП обох сторін** як юридично-значущий примірник.
- Паралельно — XML вивантаження детальних 30-min обсягів (на основі ENTSO-E `MeasurementDocument`).
- Дублювання паперовим примірником — поступово виходить з обігу з 2023 року (Закон "Про електронні документи").

### Payment terms
- Згідно постанови НКРЕКП № 641/2019 та змін 2020 (Закон № 810-IX) — ДП ГП розраховується **протягом календарного місяця, що настає за розрахунковим**. На практиці виплати тяглись з затримкою; з 2024 — D+45 to D+60.

Sources: <https://www.gpee.com.ua/>, <https://zakon.rada.gov.ua/laws/show/2019-viii> (Закон про ринок електроенергії), <https://www.nerc.gov.ua/storage/app/uploads/public/65b/161/ae8/65b161ae8a46c354816635.pdf>.

---

## 5. Telemetry / SCADA + АСКОЕ

### SCADA (operational telemetry)
- Стандарт: IEC 60870-5-104 (TCP/IP) для зв'язку об'єкт ↔ диспетчерський центр, IEC 61850 для нових об'єктів (substations).
- Polling rates типові: **1 s** (active power, frequency, voltage), **5 s** (status flags), **1 min** (агрегати).
- SCADA tag має: `point_id`, `iec_address` (IOA), `value`, `quality` (good / suspect / bad / not-topical), `timestamp` (TIMESTAMPTZ ms), `unit` (МВт, кВ, А, Гц, °С, MVar, %SoC).

### АСКОЕ (комерційний облік)
- Регулюється **Кодексом комерційного обліку** (ККО, постанова № 311/2018, із змінами останньої редакції № 1103/2025).
- **30-min інтервал** — обов'язковий для всіх ОКТ (об'єктів комерційного обліку) ≥ 50 кВт-год або потужністю ≥ 50 кВт. 15-min — заплановано до 2027 для синхронізації з MTU ENTSO-E.
- Дані передаються до **АКО (Адміністратор комерційного обліку = НЕК Укренерго)** в форматі XML (на основі ENTSO-E `MeteredDataDocument`).
- Reading frequency:
  - Smart meter → DC (data concentrator): кожні 15 хв через PLC / GSM.
  - DC → АКО: щодоби (D+1 до 10:00).
  - Корекції / валідовані дані: до D+5.

### OBIS codes (IEC 62056-61) — поширені в UA АСКОЕ
| OBIS | Значення |
|---|---|
| 1.8.0 | Сумарна активна енергія імпорт (cumulative, kWh) |
| 1.8.1 / 1.8.2 / 1.8.3 / 1.8.4 | Активна імпорт по тарифних зонах (T1 пік, T2 напівпік, T3 ніч, T4 резерв) |
| 2.8.0 | Сумарна активна експорт (для виробників / prosumerів) |
| 2.8.1..2.8.4 | Експорт по тарифних зонах |
| 3.8.0 / 4.8.0 | Реактивна імпорт / експорт |
| 1.5.0 / 2.5.0 | Поточна активна потужність імпорт / експорт (для load-profile 30-min) |
| 15.8.0 | Абсолютна сумарна (рідше) |
| 0.0.0 | Серійний номер лічильника |
| 0.9.1 / 0.9.2 | Час / дата лічильника |

### Поля одного запису load-profile
- `meter_eic` ("V" prefix у EIC схемі — це точка комерційного обліку)
- `obis_code` (text, e.g. "1.5.0")
- `interval_start` (TIMESTAMPTZ, з округленням до 30-min)
- `interval_end` (TIMESTAMPTZ)
- `value` (NUMERIC(15,4))
- `unit` (kWh / kvarh / kW)
- `quality_flag` (V — validated, E — estimated, S — substituted, R — raw)
- `direction` (IMPORT / EXPORT)

Sources: <https://www.nerc.gov.ua/acts/pro-zatverdzhennya-kodeksu-komertsiynogo-obliku-elektrichnoi-energii>, <https://ua.energy/uchasnikam_rinku/administrator-komertsijnogo-obliku/stan-komertsijnogo-obliku/>.

---

## 6. ENTSO-E codes used in UA submissions

### Bidding Zone (BZN) — area EIC
- **10Y1001C--00003F** — Ukraine BZ (єдина зона з 2022, після з'єднання з ENTSO-E і скасування окремої зони Бурштинського енергоострова).
- **10YUA-WEPS-----0** — UA-BEI (Бурштинський енергоострів), історична; досі трапляється в ENTSO-E TP для архівних даних до 2022-02-24.
- **10Y1001C--000182** — UA-IPS (об'єднана енергосистема), використовується як LFA (Load Frequency Area) / control area Укренерго.

### EIC code structure (16 символів)
- Positions **1–2**: country code (10 для України на сьогодні; раніше 46).
- Position **3**: object type — `Y` area, `X` party, `W` resource (production unit), `V` measurement point, `T` tie-line, `Z` location.
- Positions **4–15**: 12 alphanumeric symbols (issuer + serial).
- Position **16**: check character (mod-37).

### Market Time Unit (MTU)
- UA — **60 min** на сьогодні. План перехода на **15 min** до 2027 (in line with ENTSO-E SDAC).

### Business types (most used in UA)
| Code | Meaning | UA usage |
|---|---|---|
| A01 | Production | прогноз/факт generation |
| A02 | Internal trade | bilateral ДД, intra-portfolio |
| A04 | Consumption | прогноз/факт consumption |
| A05 | Balance management | БР activation |
| A60 | Minimum possible | min stable generation level |
| A61 | Maximum available | offered capacity на БР |
| A85 | Internal redispatch | переусеред в межах ОЕС |
| A86 | Cross-border redispatch | між UA та EU |
| A95 | Frequency containment reserve | РВЧ |
| A96 | Automatic frequency restoration reserve | РВЧ-2 (aFRR) |
| A97 | Manual frequency restoration reserve | резерв (mFRR) |

### Document types (most used)
| Code | Meaning |
|---|---|
| A09 | Finalised schedule |
| A17 | Aggregated energy data report |
| A24 | Bid document |
| A25 | Allocation result document |
| A44 | Price document (clearing price publication) |
| A61 | Estimated net schedule |
| A65 | System total load (load forecast / actual) |
| A71 | Generation forecast |
| A73 | Actual generation |
| A75 | Actual generation per generation unit |
| A81 | Contracted reserves |

### Process types
- A01 Day ahead
- A02 Intraday incremental
- A18 Intraday total
- A16 Realised
- A39 Synchronisation process
- A47 Balancing time-frame

Sources: <https://www.entsoe.eu/Documents/EDI/Library/Core/entso-e-code-list-v36r0.pdf>, <https://www.entsoe.eu/data/energy-identification-codes-eic/eic-approved-codes/>, <https://transparencyplatform.zendesk.com/hc/en-us/articles/15885757676308-Area-List-with-Energy-Identification-Code-EIC>.

---

## 7. КЕП / Дія.Підпис signed document structure

### Wrapper format
- **CAdES-BES** (RFC 5126) — мінімум, основний робочий формат у Дія.
- **CAdES-XL / CAdES-X-Long** — рекомендується для документів довгого зберігання (settlement statements, контракти). Включає revocation info + TSA timestamp.
- Файлова обгортка — **PKCS#7 / CMS** (.p7s), два режими:
  - **Enveloped** — підпис + контент в одному .p7s (для файлів < 5 МБ).
  - **Detached** — окремо `document.pdf` + `document.pdf.p7s` (для більших файлів і де треба відкривати оригінал).
- Стандарт алгоритмів: ДСТУ 4145-2002 (українська ECDSA-варіація на еліптичних кривих) + SHA-256 (іноді SHA-384 для нових сертифікатів) + RSA / ECDSA secp256r1 (паралельний європейський трек).

### Метадані в підпису
- `signer.subject.commonName` (П.І.Б.)
- `signer.subject.organizationName` (юр. особа)
- `signer.subject.serialNumber` ("UA-...") з ЄДРПОУ юрособи або ІПН ФОП
- `signer.subject.title` (посада)
- `certificate.issuer` (АЦСК — наприклад "АЦСК ПриватБанк", "Дія", "Ключові системи", "ІДД ДПС")
- `certificate.serialNumber` + `notBefore` / `notAfter`
- `tsa.timestamp` (RFC 3161 — від ЦЗО czo.gov.ua або АЦСК)
- `documentHash` (SHA-256 hex, 64 chars)
- `signature.algorithm` (наприклад "DSTU4145-2002-431-m")
- `policy.id` (OID політики підпису, наприклад `1.2.804.2.1.1.1.2.3.1` для CAdES-BES Україна)

### Visual representation
- В PDF — окрема **остання сторінка-додаток** "Протокол створення та перевірки кваліфікованого електронного підпису" (де перераховані всі підписанти + хеш + timestamp).
- В UI кабінетів — **бейдж "Підписано КЕП"** з іконкою щита + ім'я підписанта + дата.
- Окрема валідація на <https://czo.gov.ua/verify> або <https://ca.diia.gov.ua/verify>.

### Recommended stub UI for our DEMO
Один компактний бейдж на документі (картка / PDF preview / settlement viewer):

```
┌─────────────────────────────────────────────────────────┐
│  ✓ Підписано КЕП                                        │
│  Іваненко Іван Іванович  · ЄДРПОУ 12345678               │
│  АЦСК: «Дія»  · 2026-05-23T14:32:11+03:00                │
│  SHA-256: 9f3a…b71c  · Сертифікат: до 2027-08-01         │
└─────────────────────────────────────────────────────────┘
```

Конкретно зберігаємо в БД (`signed_documents` table — див. §9):
- `signer_name` (text)
- `signer_edrpou` (text, 8 або 10 цифр)
- `signer_ipn` (text, 10 цифр; nullable якщо юрособа)
- `acsk_name` (text — emitting CA)
- `signed_at` (TIMESTAMPTZ)
- `document_hash_sha256` (char(64))
- `cert_valid_until` (DATE)
- `signature_format` ('CAdES-BES' / 'CAdES-X-Long')
- `kep_badge_short` (computed — текст бейджа для UI)

Sources: <https://czo.gov.ua/testexamples>, <https://uakey.com.ua/news/main/cades-x-long-format-dlja-dovgotrivalogo-zbergannja-kep>, <https://ca.diia.gov.ua/>.

---

## 8. Регуляторні події / Regulator notices

### НКРЕКП постанова — структура
- `Тип акта` — Постанова / Розпорядження / Рішення.
- `Номер` (зростаючий по календарному року, наприклад "№ 1462").
- `Дата прийняття` (DATE).
- `Заголовок` ("Про затвердження ...", "Про внесення змін до ...", "Про встановлення тарифів для ...").
- `Орган` — Національна комісія, що здійснює державне регулювання у сферах енергетики та комунальних послуг.
- `Affected entities` — текстове поле / список ЄДРПОУ (у тарифних рішеннях).
- `Effective date` — окремо в тексті, often "з 1 січня 20XX року".
- `Реєстрація в Мін'юсті` (номер + дата) — для регуляторних актів, що зачіпають права.
- `URL публікації` на nerc.gov.ua + Офіційний вісник України.
- Санкції — окремий тип постанов "Про застосування санкції до ...", з полями: суб'єкт, ЄДРПОУ, стаття порушення, сума штрафу (грн).

### Tariff change events
- Поля: тарифний клас (передача / розподіл / постачання / зелений тариф / РСВ), ЄДРПОУ ліцензіата, попередній тариф, новий тариф (грн/МВт·год або грн/кВт·год), дата набуття чинності.

### Market freeze / emergency
- Виданням Укренерго (диспетчерська команда) + НКРЕКП-підтвердження.
- Поля: тип події (graphic shutdowns / aFRR suspension / трансгран. ban), час початку (TIMESTAMPTZ), час очікуваного завершення, area scope (область / IPS / okremye вузли).

### Where published
- <https://www.nerc.gov.ua/acts/> — основне джерело.
- Офіційний вісник України (paper of record).
- Дублюється в Energy Map (ua-energy.org/uk).

Sources: <https://www.nerc.gov.ua/>, <https://www.nerc.gov.ua/acts/>.

---

## 9. Recommended Postgres table structures (v2 synthetic dataset)

Поля — pseudo-DDL. Усі рядки несуть `tenant_id` для multi-tenant ізоляції. Часові поля — `TIMESTAMPTZ` з Europe/Kyiv як логічна зона представлення.

### 9.1 `forecast_submissions`
```sql
CREATE TABLE forecast_submissions (
    id                 BIGSERIAL PRIMARY KEY,
    tenant_id          UUID NOT NULL,
    submission_id      TEXT NOT NULL,            -- mRID
    submitted_at       TIMESTAMPTZ NOT NULL,
    submitter_eic      CHAR(16) NOT NULL,        -- X-prefix party EIC
    resource_eic       CHAR(16),                 -- W-prefix; null для агрегату
    bzn_eic            CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
    business_type      CHAR(3) NOT NULL,         -- A01 / A04 / A85 ...
    document_type      CHAR(3) NOT NULL,         -- A09 / A71 / A65
    process_type       CHAR(3) NOT NULL,         -- A01 day-ahead
    delivery_date      DATE NOT NULL,
    resolution_minutes SMALLINT NOT NULL DEFAULT 60, -- 60 / 30 / 15
    position           SMALLINT NOT NULL,        -- 1..24 (or 1..96)
    interval_start     TIMESTAMPTZ NOT NULL,
    quantity_mwh       NUMERIC(12,4) NOT NULL,
    status             TEXT NOT NULL,            -- DRAFT / SUBMITTED / ACK / REJECTED
    raw_xml            TEXT                       -- generated stub
);
CREATE INDEX ON forecast_submissions (tenant_id, delivery_date, interval_start);
CREATE INDEX ON forecast_submissions (resource_eic, interval_start);
-- partition: monthly RANGE by delivery_date
```
Expected rows for demo: 3 tenants × ~5 assets × 24 slots/day × 90 days = **~32 400**.

### 9.2 `market_bids`
```sql
CREATE TABLE market_bids (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           UUID NOT NULL,
    bid_id              TEXT NOT NULL,            -- mRID
    market              TEXT NOT NULL,            -- 'RDN' | 'VDR' | 'BR' | 'DD'
    delivery_date       DATE NOT NULL,
    hour                SMALLINT NOT NULL,        -- 0..23
    interval_start      TIMESTAMPTZ NOT NULL,
    interval_end        TIMESTAMPTZ NOT NULL,
    side                TEXT NOT NULL,            -- 'BUY' | 'SELL'
    bid_type            TEXT NOT NULL,            -- 'SIMPLE' | 'BLOCK' | 'STEP' | 'LIMIT' | 'IOC' | 'FOK'
    block_id            UUID,
    volume_mwh          NUMERIC(10,3) NOT NULL,
    price_uah_mwh       NUMERIC(10,2) NOT NULL,
    technology_type     CHAR(3),                  -- B01..B25 ENTSO-E PsrType
    participant_eic     CHAR(16) NOT NULL,
    resource_eic        CHAR(16),
    submitted_at        TIMESTAMPTZ NOT NULL,
    state               TEXT NOT NULL,            -- 'ACTIVE' | 'ACCEPTED' | 'PARTIAL' | 'REJECTED' | 'CANCELLED'
    accepted_volume_mwh NUMERIC(10,3),
    clearing_price      NUMERIC(10,2),
    settlement_amount   NUMERIC(14,2)
);
CREATE INDEX ON market_bids (tenant_id, market, delivery_date, hour);
CREATE INDEX ON market_bids (resource_eic, interval_start);
-- partition: monthly RANGE by delivery_date
```
Expected rows: 3 tenants × ~3 markets (РДН+ВДР+БР) × 24h × 90 days ≈ **~19 500**, + intraday updates ~ **+10 000**.

### 9.3 `settlement_statements`
```sql
CREATE TABLE settlement_statements (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           UUID NOT NULL,
    statement_no        TEXT NOT NULL,
    counterparty        TEXT NOT NULL,            -- 'ДП Гарантований Покупець' | 'НЕК Укренерго' | 'ОРЕЕ' | bilateral name
    counterparty_edrpou TEXT,
    contract_no         TEXT,
    period_year         SMALLINT NOT NULL,
    period_month        SMALLINT NOT NULL,
    period_start        DATE NOT NULL,
    period_end          DATE NOT NULL,
    volume_total_mwh    NUMERIC(14,4) NOT NULL,
    amount_net_uah      NUMERIC(14,2) NOT NULL,
    vat_rate            NUMERIC(4,2) NOT NULL,    -- 0.00 / 0.20 / 0.07
    amount_vat_uah      NUMERIC(14,2) NOT NULL,
    amount_gross_uah    NUMERIC(14,2) NOT NULL,
    payment_due_date    DATE NOT NULL,
    payment_received_at TIMESTAMPTZ,
    status              TEXT NOT NULL,            -- 'DRAFT' | 'ISSUED' | 'SIGNED' | 'PAID' | 'DISPUTED'
    signed_doc_id       BIGINT REFERENCES signed_documents(id)
);
CREATE TABLE settlement_statement_lines (
    id                  BIGSERIAL PRIMARY KEY,
    statement_id        BIGINT REFERENCES settlement_statements(id) ON DELETE CASCADE,
    line_no             SMALLINT NOT NULL,
    asset_eic           CHAR(16) NOT NULL,
    asset_name          TEXT NOT NULL,
    technology_type     CHAR(3),
    volume_mwh          NUMERIC(12,4) NOT NULL,
    tariff_uah_mwh      NUMERIC(10,2) NOT NULL,
    amount_uah          NUMERIC(14,2) NOT NULL
);
CREATE INDEX ON settlement_statements (tenant_id, period_year, period_month);
```
Expected rows: 3 tenants × 3 months × ~3 counterparties = **~27 statements**, ~5 lines each.

### 9.4 `telemetry_points` (time-series, hot path)
```sql
CREATE TABLE telemetry_points (
    tenant_id           UUID NOT NULL,
    point_id            UUID NOT NULL,
    meter_eic           CHAR(16),                 -- V-prefix for metering point
    obis_code           TEXT,                     -- e.g. '1.5.0'
    ts                  TIMESTAMPTZ NOT NULL,
    interval_minutes    SMALLINT NOT NULL,        -- 1, 5, 30
    value               NUMERIC(15,4) NOT NULL,
    unit                TEXT NOT NULL,            -- 'MW' | 'MWh' | 'kV' | '%SoC' | 'Hz'
    direction           TEXT,                     -- 'IMPORT' | 'EXPORT' | NULL
    quality             CHAR(1) NOT NULL DEFAULT 'R'  -- R raw, V validated, E estimated, S substituted
) PARTITION BY RANGE (ts);
-- one partition per month: telemetry_points_2026_05
CREATE INDEX ON telemetry_points (tenant_id, point_id, ts DESC);
CREATE INDEX ON telemetry_points (meter_eic, ts DESC);
```
**Partition strategy:** RANGE по `ts` місячно. Для частих запитів дашборду — додатковий materialised view агрегатів 30-min / 1h.
Expected rows: 3 tenants × ~15 telemetry points × 1-min × 90 days = **~5.8 million** (можна знизити до ~1 min hot, 30-min cold, або просто 30-min для лічильникових OBIS, 1-min тільки для активної потужності).

### 9.5 `regulator_events`
```sql
CREATE TABLE regulator_events (
    id              BIGSERIAL PRIMARY KEY,
    issuer          TEXT NOT NULL,                -- 'НКРЕКП' | 'Укренерго' | 'Кабмін'
    act_type        TEXT NOT NULL,                -- 'Постанова' | 'Розпорядження' | 'Команда диспетчера' | 'Тарифне рішення'
    act_number      TEXT,
    issued_at       DATE NOT NULL,
    effective_at    DATE,
    title           TEXT NOT NULL,
    category        TEXT,                          -- 'TARIFF' | 'CODE_AMENDMENT' | 'SANCTION' | 'EMERGENCY' | 'MARKET_FREEZE'
    affected_entities JSONB,                       -- [{"edrpou":"12345678","name":"..."}]
    affected_tenants UUID[],                       -- which demo tenants see this
    severity        TEXT,                          -- 'INFO' | 'NOTICE' | 'WARN' | 'CRITICAL'
    summary         TEXT NOT NULL,
    source_url      TEXT,
    full_text       TEXT
);
CREATE INDEX ON regulator_events (issued_at DESC);
CREATE INDEX ON regulator_events USING GIN (affected_entities);
```
Expected rows: ~30 для 90-day demo period (tariff changes, code amendments, fictional sanctions, emergency drills).

### 9.6 `signed_documents` (КЕП stub)
```sql
CREATE TABLE signed_documents (
    id                    BIGSERIAL PRIMARY KEY,
    tenant_id             UUID NOT NULL,
    document_type         TEXT NOT NULL,           -- 'SETTLEMENT_ACT' | 'BID_PACKAGE' | 'FORECAST_PACKAGE' | 'CONTRACT'
    document_ref_table    TEXT NOT NULL,           -- 'settlement_statements'
    document_ref_id       BIGINT NOT NULL,
    signer_name           TEXT NOT NULL,
    signer_position       TEXT,
    signer_edrpou         TEXT,
    signer_ipn            TEXT,
    acsk_name             TEXT NOT NULL,           -- 'Дія' | 'ПриватБанк' | 'ІДД ДПС' | 'Ключові системи'
    signature_format      TEXT NOT NULL DEFAULT 'CAdES-X-Long',
    document_hash_sha256  CHAR(64) NOT NULL,
    signed_at             TIMESTAMPTZ NOT NULL,
    tsa_provider          TEXT,                    -- 'czo.gov.ua' | 'ca.diia.gov.ua'
    cert_serial           TEXT,
    cert_valid_until      DATE,
    p7s_blob              BYTEA,                   -- stub: random bytes
    kep_badge_short       TEXT GENERATED ALWAYS AS (
        signer_name || ' · ЄДРПОУ ' || COALESCE(signer_edrpou, signer_ipn) ||
        ' · ' || TO_CHAR(signed_at,'YYYY-MM-DD HH24:MI')
    ) STORED
);
CREATE INDEX ON signed_documents (document_ref_table, document_ref_id);
```
Expected rows: один підпис на кожен settlement act + один на пакет bids/forecasts на день = **~30 + 90 ≈ 120 rows** для 90-day demo.

---

## Open gaps / what we'll have to fake outright

1. **Реальні XML schemas з ОРЕЕ / Укренерго** — публічно не викладені цілком; в кабінеті учасника. Ми генеруємо stub XML по ENTSO-E ESS/EDIEL зразках — це достатньо credible.
2. **Точний gate-closure schedule 2026** — змінюється; на демо фіксуємо 12:30 D-1 з підписом "actual gate publication: ОРЕЕ".
3. **Конкретні OBIS-карти конкретного типу лічильника** — варіюються (Landis+Gyr E450, Iskra MT382, ELGAMA EPQS) — ми зашиваємо універсальний набір з §5.
4. **Реальні підписи КЕП** — фейкимо метадані + випадкові SHA-256 + випадкові .p7s байти. Жодного спроби симулювати валідну криптографію.
5. **Поточна редакція ККО і КСП** на дату демо — beruчи остання редакція з 01.01.2026 (постанова № 1462/2025) як baseline; не tracking щотижневих оновлень nerc.gov.ua.

---

## Sources

- НКРЕКП, постанова № 307 від 14.03.2018 "Про затвердження Правил ринку" — <https://www.nerc.gov.ua/acts/pro-zatverdzhennya-pravil-rinku>
- НКРЕКП, постанова № 309 від 14.03.2018 "Про затвердження Кодексу системи передачі" — <https://www.nerc.gov.ua/acts/pro-zatverdzhennya-kodeksu-sistemi-peredachi>
- НКРЕКП, постанова № 311 від 14.03.2018 "Про затвердження Кодексу комерційного обліку електричної енергії" — <https://www.nerc.gov.ua/acts/pro-zatverdzhennya-kodeksu-komertsiynogo-obliku-elektrichnoi-energii>
- НКРЕКП, постанова № 1462 від 2025 "Зміни до Кодексу системи передачі" (з 01.01.2026) — <https://ua.energy/electricity-market/propozytsiyi-ta-protokoly-uk/zminy-do-kodeksu-systemy-peredachi-shho-nabyrayut-chynnosti-z-01-sichnya-2026-roku/>
- ОРЕЕ (ДП "Оператор ринку") — <https://www.oree.com.ua/>
- НЕК "Укренерго" — Адміністратор комерційного обліку, реєстрація учасників, БР — <https://ua.energy/for_market_participants/>, <https://ua.energy/uchasnikam_rinku/administrator-komertsijnogo-obliku/stan-komertsijnogo-obliku/>
- ДП "Гарантований Покупець" — типовий договір зеленого тарифу — <https://www.gpee.com.ua/>
- ENTSO-E Code Lists v36r0 — <https://www.entsoe.eu/Documents/EDI/Library/Core/entso-e-code-list-v36r0.pdf>
- ENTSO-E EIC approved codes — <https://www.entsoe.eu/data/energy-identification-codes-eic/eic-approved-codes/>
- ENTSO-E Transparency Platform — Area List with EIC — <https://transparencyplatform.zendesk.com/hc/en-us/articles/15885757676308>
- ЦЗО (Центральний засвідчувальний орган) — тестові приклади КЕП — <https://czo.gov.ua/testexamples>
- Дія.Підпис — <https://ca.diia.gov.ua/>, <https://diia.gov.ua/services/pidpisannya-dokumentiv>
- CAdES-X Long technical reference (UAKey) — <https://uakey.com.ua/news/main/cades-x-long-format-dlja-dovgotrivalogo-zbergannja-kep>
- Energy Map (UA datasets, EIC register) — <https://map.ua-energy.org/uk/resources/cf812168-a7f1-4130-a44a-3771f0bb2bf9/>
