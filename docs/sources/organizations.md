# Organizations

Generated from `ingest/hoshizora_ingest/reference/*.toml` by `uv run hoshizora docs`.
Do not edit by hand: a test fails when this file and the TOML disagree.

## How the model works

- **Identity.** Every Launch Library 2 agency becomes one `core.organization`, reached through the
  alias `ll2.agency/<id>`. Organizations that only CelesTrak knows (for example ORBCOMM) are
  curated here and reached through `hoshizora/<slug>`.
- **Type.** LL2 agency types map as Government → agency, Commercial and Private → company,
  Multinational → international, Educational → academic. Curation overrides the facts the source
  gets wrong: state-owned corporations such as CASC are companies, armed forces are military.
  Unknown LL2 types leave the type empty and appear in the data-quality report.
- **Names.** `name_en` comes from LL2 unless curated. Every `name_ja` cites its source, the
  organization's Japanese site or Japanese Wikipedia; names without one are reported as missing,
  never machine-transliterated.
- **Programs.** A program groups the agencies, companies and armed forces of one nation, so the UI
  can honestly say "Japan's launches" even when the provider is Mitsubishi Heavy Industries.
- **CelesTrak owner codes** are countries, joint ventures or organizations, not agencies. A `US`
  object can belong to NASA, the military or a company, so owner codes resolve to countries unless
  the code itself names an organization. `CIS` resolves to Russia as the USSR's successor state.
- **Fail loudly.** Every code seen in the data is recorded; codes missing from this vocabulary, and
  vocabulary entries without a mapping, appear in `hoshizora dq` and fail `--strict`.

## Programs

| Slug | English | 日本語 | Members |
|---|---|---|---|
| japan | Japan | 日本 | ll2.agency/37, ll2.agency/98, ll2.agency/94, ll2.agency/1002, ll2.agency/1083, ll2.agency/1009, ll2.agency/228 |
| china | China | 中国 | ll2.agency/17, ll2.agency/88, ll2.agency/184, ll2.agency/189, ll2.agency/1034, ll2.agency/1035, ll2.agency/1036, ll2.agency/1037, ll2.agency/177, ll2.agency/194, ll2.agency/1021, ll2.agency/259, ll2.agency/1040, ll2.agency/274, ll2.agency/1049, ll2.agency/1080, ll2.agency/1102, ll2.agency/162 |
| russia | Russia and the Soviet Union | ロシア・ソ連 | ll2.agency/63, ll2.agency/66, ll2.agency/193, ll2.agency/163, ll2.agency/175, ll2.agency/270, ll2.agency/96, ll2.agency/111, ll2.agency/103, ll2.agency/1000, ll2.agency/97, ll2.agency/119, ll2.agency/117, ll2.agency/118, ll2.agency/123, ll2.agency/187 |
| usa | United States | アメリカ | ll2.agency/44, ll2.agency/121, ll2.agency/124, ll2.agency/257, ll2.agency/147, ll2.agency/141, ll2.agency/265, ll2.agency/179, ll2.agency/100, ll2.agency/80, ll2.agency/82, ll2.agency/153, ll2.agency/1014, ll2.agency/106, ll2.agency/161, ll2.agency/1041, ll2.agency/165, ll2.agency/166, ll2.agency/181, ll2.agency/271, ll2.agency/199, ll2.agency/285, ll2.agency/266 |
| europe | Europe | 欧州 | ll2.agency/27, ll2.agency/115, ll2.agency/1044, ll2.agency/159, ll2.agency/46, ll2.agency/29, ll2.agency/36, ll2.agency/1046, ll2.agency/1045, ll2.agency/1015, ll2.agency/1019 |
| india | India | インド | ll2.agency/31, ll2.agency/190, ll2.agency/1099 |
| south-korea | South Korea | 韓国 | ll2.agency/41, ll2.agency/1089, ll2.agency/1079 |
| israel | Israel | イスラエル | ll2.agency/35, ll2.agency/95 |
| iran | Iran | イラン | ll2.agency/34, ll2.agency/1032 |
| north-korea | North Korea | 北朝鮮 | ll2.agency/40, ll2.agency/1074 |

## Curated organizations

| Key | Slug | English override | 日本語 (source) | Type override | Countries |
|---|---|---|---|---|---|
| ll2.agency/44 | nasa |  | [アメリカ航空宇宙局](<https://ja.wikipedia.org/wiki/アメリカ航空宇宙局>) |  |  |
| ll2.agency/27 | esa |  | [欧州宇宙機関](<https://ja.wikipedia.org/wiki/欧州宇宙機関>) |  |  |
| ll2.agency/37 | jaxa |  | [宇宙航空研究開発機構](<https://ja.wikipedia.org/wiki/宇宙航空研究開発機構>) |  |  |
| ll2.agency/17 | cnsa |  | [中国国家航天局](<https://ja.wikipedia.org/wiki/中国国家航天局>) |  |  |
| ll2.agency/63 | roscosmos | Roscosmos | [ロスコスモス](<https://ja.wikipedia.org/wiki/ロスコスモス>) |  |  |
| ll2.agency/31 | isro | Indian Space Research Organisation | [インド宇宙研究機関](<https://ja.wikipedia.org/wiki/インド宇宙研究機関>) |  |  |
| ll2.agency/121 | spacex |  | [スペースX](<https://ja.wikipedia.org/wiki/スペースX>) |  |  |
| ll2.agency/88 | casc |  | [中国航天科技集団](<https://ja.wikipedia.org/wiki/中国航天科技集団>) | company |  |
| ll2.agency/184 | casic |  | [中国航天科工集団](<https://ja.wikipedia.org/wiki/中国航天科工集団>) | company |  |
| ll2.agency/189 |  |  |  | company |  |
| ll2.agency/1034 |  |  |  |  |  |
| ll2.agency/1035 |  |  |  |  |  |
| ll2.agency/1036 |  |  |  |  |  |
| ll2.agency/1037 |  |  |  |  |  |
| ll2.agency/177 | cgwic |  |  |  |  |
| ll2.agency/194 | expace |  |  |  |  |
| ll2.agency/1021 | galactic-energy |  |  |  |  |
| ll2.agency/259 | landspace |  | [ランドスペース](<https://ja.wikipedia.org/wiki/ランドスペース>) |  |  |
| ll2.agency/1040 | cas-space |  |  |  |  |
| ll2.agency/274 | i-space |  | [星際栄耀](<https://ja.wikipedia.org/wiki/星際栄耀>) |  |  |
| ll2.agency/1049 | space-pioneer |  |  |  |  |
| ll2.agency/1080 | orienspace |  |  |  |  |
| ll2.agency/1102 | deep-blue-aerospace |  |  |  |  |
| ll2.agency/162 | pla |  | [中国人民解放軍](<https://ja.wikipedia.org/wiki/中国人民解放軍>) | military |  |
| ll2.agency/98 | mhi |  | [三菱重工業](<https://ja.wikipedia.org/wiki/三菱重工業>) |  |  |
| ll2.agency/94 | ihi |  | [IHI](<https://ja.wikipedia.org/wiki/IHI>) |  |  |
| ll2.agency/1002 | interstellar-technologies |  | [インターステラテクノロジズ](<https://ja.wikipedia.org/wiki/インターステラテクノロジズ>) |  |  |
| ll2.agency/1083 | space-one |  |  |  |  |
| ll2.agency/1009 | isas |  | [宇宙科学研究所](<https://ja.wikipedia.org/wiki/宇宙科学研究所>) |  |  |
| ll2.agency/228 | nasda |  | [宇宙開発事業団](<https://ja.wikipedia.org/wiki/宇宙開発事業団>) |  |  |
| ll2.agency/1085 | mitsubishi-electric |  | [三菱電機](<https://ja.wikipedia.org/wiki/三菱電機>) |  |  |
| ll2.agency/66 | soviet-space-program |  | [ソビエト連邦の宇宙開発](<https://ja.wikipedia.org/wiki/ソビエト連邦の宇宙開発>) |  |  |
| ll2.agency/193 | russian-space-forces |  | [ロシア宇宙軍](<https://ja.wikipedia.org/wiki/ロシア宇宙軍>) | military |  |
| ll2.agency/163 | russian-aerospace-defence-forces |  | [ロシア航空宇宙防衛軍](<https://ja.wikipedia.org/wiki/ロシア航空宇宙防衛軍>) | military |  |
| ll2.agency/175 | russian-ministry-of-defence |  | [ロシア国防省](<https://ja.wikipedia.org/wiki/ロシア国防省>) | military |  |
| ll2.agency/270 | strategic-rocket-forces |  | [ロシア戦略ロケット軍](<https://ja.wikipedia.org/wiki/ロシア戦略ロケット軍>) | military |  |
| ll2.agency/96 | khrunichev |  | [クルニチェフ国家研究生産宇宙センター](<https://ja.wikipedia.org/wiki/クルニチェフ国家研究生産宇宙センター>) | company |  |
| ll2.agency/111 | progress-rocket-space-centre |  | [プログレス国家研究生産ロケット宇宙センター](<https://ja.wikipedia.org/wiki/プログレス国家研究生産ロケット宇宙センター>) |  |  |
| ll2.agency/103 | energia |  | [S.P.コロリョフ ロケット&スペース コーポレーション エネルギア](<https://ja.wikipedia.org/wiki/S.P.コロリョフ_ロケット&スペース_コーポレーション_エネルギア>) |  |  |
| ll2.agency/1000 |  |  |  |  |  |
| ll2.agency/97 | lavochkin |  | [S・A・ラヴォーチキン記念科学製造合同](<https://ja.wikipedia.org/wiki/S・A・ラヴォーチキン記念科学製造合同>) |  |  |
| ll2.agency/119 | kosmotras |  | [ISCコスモトラス](<https://ja.wikipedia.org/wiki/ISCコスモトラス>) |  |  |
| ll2.agency/117 | eurockot |  | [ユーロコット](<https://ja.wikipedia.org/wiki/ユーロコット>) |  |  |
| ll2.agency/118 | ils |  | [インターナショナル・ローンチ・サービス](<https://ja.wikipedia.org/wiki/インターナショナル・ローンチ・サービス>) |  |  |
| ll2.agency/123 | starsem |  | [スターセム](<https://ja.wikipedia.org/wiki/スターセム>) |  |  |
| ll2.agency/187 |  |  |  |  |  |
| ll2.agency/124 | ula |  | [ユナイテッド・ローンチ・アライアンス](<https://ja.wikipedia.org/wiki/ユナイテッド・ローンチ・アライアンス>) |  |  |
| ll2.agency/257 | northrop-grumman |  | [ノースロップ・グラマン](<https://ja.wikipedia.org/wiki/ノースロップ・グラマン>) |  |  |
| ll2.agency/147 | rocket-lab |  | [ロケット・ラボ](<https://ja.wikipedia.org/wiki/ロケット・ラボ>) |  |  |
| ll2.agency/141 | blue-origin |  | [ブルーオリジン](<https://ja.wikipedia.org/wiki/ブルーオリジン>) |  |  |
| ll2.agency/265 | firefly-aerospace |  | [ファイアフライ・エアロスペース](<https://ja.wikipedia.org/wiki/ファイアフライ・エアロスペース>) |  |  |
| ll2.agency/179 | orbital-atk |  |  |  |  |
| ll2.agency/100 | orbital-sciences |  | [オービタル・サイエンシズ](<https://ja.wikipedia.org/wiki/オービタル・サイエンシズ>) |  |  |
| ll2.agency/80 | boeing |  | [ボーイング](<https://ja.wikipedia.org/wiki/ボーイング>) |  |  |
| ll2.agency/82 | lockheed-martin |  | [ロッキード・マーティン](<https://ja.wikipedia.org/wiki/ロッキード・マーティン>) |  |  |
| ll2.agency/153 | mcdonnell-douglas |  | [マクドネル・ダグラス](<https://ja.wikipedia.org/wiki/マクドネル・ダグラス>) |  |  |
| ll2.agency/1014 | martin-marietta |  | [マーティン・マリエッタ](<https://ja.wikipedia.org/wiki/マーティン・マリエッタ>) |  |  |
| ll2.agency/106 |  |  |  |  |  |
| ll2.agency/161 | usaf |  | [アメリカ空軍](<https://ja.wikipedia.org/wiki/アメリカ空軍>) | military |  |
| ll2.agency/1041 | ussf |  | [アメリカ宇宙軍](<https://ja.wikipedia.org/wiki/アメリカ宇宙軍>) | military |  |
| ll2.agency/165 | us-army |  | [アメリカ陸軍](<https://ja.wikipedia.org/wiki/アメリカ陸軍>) | military |  |
| ll2.agency/166 | us-navy |  | [アメリカ海軍](<https://ja.wikipedia.org/wiki/アメリカ海軍>) | military |  |
| ll2.agency/181 | nro |  | [アメリカ国家偵察局](<https://ja.wikipedia.org/wiki/アメリカ国家偵察局>) | military |  |
| ll2.agency/271 |  |  |  | military |  |
| ll2.agency/1025 |  |  |  | military |  |
| ll2.agency/213 |  |  |  | military |  |
| ll2.agency/1056 |  |  |  | military |  |
| ll2.agency/199 | virgin-orbit |  | [ヴァージン・オービット](<https://ja.wikipedia.org/wiki/ヴァージン・オービット>) |  |  |
| ll2.agency/285 | astra |  | [アストラ](<https://ja.wikipedia.org/wiki/アストラ_(航空宇宙企業)>) |  |  |
| ll2.agency/266 | relativity-space |  | [レラティビティ・スペース](<https://ja.wikipedia.org/wiki/レラティビティ・スペース>) |  |  |
| ll2.agency/115 | arianespace |  | [アリアンスペース](<https://ja.wikipedia.org/wiki/アリアンスペース>) |  |  |
| ll2.agency/1044 | arianegroup |  |  |  |  |
| ll2.agency/159 | avio |  | [アヴィオ](<https://ja.wikipedia.org/wiki/アヴィオ>) |  |  |
| ll2.agency/46 | cnes |  | [フランス国立宇宙研究センター](<https://ja.wikipedia.org/wiki/フランス国立宇宙研究センター>) |  |  |
| ll2.agency/29 | dlr |  | [ドイツ航空宇宙センター](<https://ja.wikipedia.org/wiki/ドイツ航空宇宙センター>) |  |  |
| ll2.agency/36 | asi |  | [イタリア宇宙機関](<https://ja.wikipedia.org/wiki/イタリア宇宙機関>) |  |  |
| ll2.agency/1046 | isar-aerospace |  |  |  |  |
| ll2.agency/1045 | rocket-factory-augsburg |  |  |  |  |
| ll2.agency/1015 | eldo |  | [欧州ロケット開発機構](<https://ja.wikipedia.org/wiki/欧州ロケット開発機構>) |  |  |
| ll2.agency/1019 | esro |  | [欧州宇宙研究機構](<https://ja.wikipedia.org/wiki/欧州宇宙研究機構>) |  |  |
| ll2.agency/190 | antrix |  |  |  |  |
| ll2.agency/1099 | skyroot-aerospace |  |  |  |  |
| ll2.agency/41 | kari |  | [韓国航空宇宙研究院](<https://ja.wikipedia.org/wiki/韓国航空宇宙研究院>) |  |  |
| ll2.agency/1089 | kasa |  | [韓国航空宇宙庁](<https://ja.wikipedia.org/wiki/韓国航空宇宙庁>) |  |  |
| ll2.agency/1079 | add |  | [国防科学研究所](<https://ja.wikipedia.org/wiki/国防科学研究所_(大韓民国)>) | military |  |
| ll2.agency/35 | israel-space-agency |  | [イスラエル宇宙局](<https://ja.wikipedia.org/wiki/イスラエル宇宙局>) |  |  |
| ll2.agency/95 | iai |  | [イスラエル・エアロスペース・インダストリーズ](<https://ja.wikipedia.org/wiki/イスラエル・エアロスペース・インダストリーズ>) |  |  |
| ll2.agency/34 | iranian-space-agency |  | [イラン宇宙機関](<https://ja.wikipedia.org/wiki/イラン宇宙機関>) |  |  |
| ll2.agency/1032 | irgc-aerospace-force |  |  | military |  |
| ll2.agency/40 | kcst |  | [朝鮮宇宙空間技術委員会](<https://ja.wikipedia.org/wiki/朝鮮宇宙空間技術委員会>) |  |  |
| ll2.agency/1074 | nada |  |  |  |  |
| ll2.agency/16 | csa |  | [カナダ宇宙庁](<https://ja.wikipedia.org/wiki/カナダ宇宙庁>) |  |  |
| ll2.agency/13 | uksa |  | [イギリス宇宙局](<https://ja.wikipedia.org/wiki/イギリス宇宙局>) |  |  |
| ll2.agency/160 |  |  |  | military |  |
| ll2.agency/227 |  |  |  | military |  |
| ll2.agency/253 |  |  |  | military |  |
| ll2.agency/233 |  |  |  | military |  |
| ll2.agency/1050 |  |  |  | military |  |
| ll2.agency/1053 |  |  |  | military |  |
| ll2.agency/1055 |  |  |  | military |  |
| ll2.agency/232 | eumetsat |  | [欧州気象衛星開発機構](<https://ja.wikipedia.org/wiki/欧州気象衛星開発機構>) |  |  |
| ll2.agency/229 | eutelsat |  | [ユーテルサット](<https://ja.wikipedia.org/wiki/ユーテルサット>) |  |  |
| ll2.agency/204 | globalstar |  | [グローバルスター](<https://ja.wikipedia.org/wiki/グローバルスター>) |  |  |
| ll2.agency/205 | inmarsat |  | [インマルサット](<https://ja.wikipedia.org/wiki/インマルサット>) |  |  |
| ll2.agency/202 | iridium |  | [イリジウムコミュニケーションズ](<https://ja.wikipedia.org/wiki/イリジウムコミュニケーションズ>) |  |  |
| ll2.agency/206 | intelsat |  | [インテルサット](<https://ja.wikipedia.org/wiki/インテルサット>) |  |  |
| ll2.agency/207 | arabsat |  |  |  |  |
| ll2.agency/245 | rascom |  |  |  |  |
| ll2.agency/122 | sea-launch |  | [シーローンチ](<https://ja.wikipedia.org/wiki/シーローンチ>) |  |  |
| ll2.agency/203 | ses |  | [SES](<https://ja.wikipedia.org/wiki/SES_(企業)>) |  |  |
| hoshizora/abs | abs | Asia Broadcast Satellite |  | company |  |
| hoshizora/asiasat | asiasat | Asia Satellite Telecommunications Company (AsiaSat) | [アジアサット](<https://ja.wikipedia.org/wiki/アジアサット>) | company | HK |
| hoshizora/iss | iss | International Space Station partnership | [国際宇宙ステーション](<https://ja.wikipedia.org/wiki/国際宇宙ステーション>) | international |  |
| hoshizora/nato | nato | North Atlantic Treaty Organization | [北大西洋条約機構](<https://ja.wikipedia.org/wiki/北大西洋条約機構>) | international |  |
| hoshizora/new-ico | new-ico | New ICO |  | company |  |
| hoshizora/o3b | o3b | O3b Networks |  | company |  |
| hoshizora/orbcomm | orbcomm | ORBCOMM |  | company | US |

## CelesTrak owner codes

Source: <https://celestrak.org/satcat/sources.php>, retrieved 2026-10-16.

| Code | CelesTrak label | Maps to | Note |
|---|---|---|---|
| AB | Arab Satellite Communications Organization | organization `arabsat` |  |
| ABS | Asia Broadcast Satellite | organization `abs` |  |
| AC | Asia Satellite Telecommunications Company (ASIASAT) | organization `asiasat` |  |
| ALG | Algeria | DZ |  |
| ANG | Angola | AO |  |
| ARGN | Argentina | AR |  |
| ARM | Republic of Armenia | AM |  |
| ASRA | Austria | AT |  |
| AUS | Australia | AU |  |
| AZER | Azerbaijan | AZ |  |
| BEL | Belgium | BE |  |
| BELA | Belarus | BY |  |
| BERM | Bermuda | BM |  |
| BGD | Peoples Republic of Bangladesh | BD |  |
| BHR | The Kingdom of Bahrain | BH |  |
| BHUT | The Kingdom of Bhutan | BT |  |
| BOL | Bolivia | BO |  |
| BRAZ | Brazil | BR |  |
| BUL | Bulgaria | BG |  |
| BWA | Republic of Botswana | BW |  |
| CA | Canada | CA |  |
| CHBZ | China/Brazil | CN, BR |  |
| CHLE | Chile | CL |  |
| CHTU | China/Türkiye | CN, TR |  |
| CIS | Commonwealth of Independent States (former USSR) | RU | Attributed to Russia as the USSR's successor state; SATCAT uses CIS for Soviet and Russian objects. |
| COL | Colombia | CO |  |
| CRI | Republic of Costa Rica | CR |  |
| CZCH | Czech Republic (former Czechoslovakia) | CZ |  |
| DEN | Denmark | DK |  |
| DJI | Republic of Djibouti | DJ |  |
| ECU | Ecuador | EC |  |
| EGYP | Egypt | EG |  |
| ESA | European Space Agency | organization `esa` |  |
| ESRO | European Space Research Organization | organization `esro` |  |
| EST | Estonia | EE |  |
| ETH | Ethiopia | ET |  |
| EUME | European Organization for the Exploitation of Meteorological Satellites (EUMETSAT) | organization `eumetsat` |  |
| EUTE | European Telecommunications Satellite Organization (EUTELSAT) | organization `eutelsat` |  |
| FGER | France/Germany | FR, DE |  |
| FIN | Finland | FI |  |
| FR | France | FR |  |
| FRIT | France/Italy | FR, IT |  |
| GER | Germany | DE |  |
| GHA | Republic of Ghana | GH |  |
| GLOB | Globalstar | organization `globalstar` |  |
| GREC | Greece | GR |  |
| GRSA | Greece/Saudi Arabia | GR, SA |  |
| GUAT | Guatemala | GT |  |
| HRV | Republic of Croatia | HR |  |
| HUN | Hungary | HU |  |
| IM | International Mobile Satellite Organization (INMARSAT) | organization `inmarsat` |  |
| IND | India | IN |  |
| INDO | Indonesia | ID |  |
| IRAN | Iran | IR |  |
| IRAQ | Iraq | IQ |  |
| IRID | Iridium | organization `iridium` |  |
| IRL | Ireland | IE |  |
| ISRA | Israel | IL |  |
| ISRO | Indian Space Research Organisation | organization `isro` |  |
| ISS | International Space Station | organization `iss` |  |
| IT | Italy | IT |  |
| ITSO | International Telecommunications Satellite Organization (INTELSAT) | organization `intelsat` |  |
| JOR | Jordan | JO | Not on the CelesTrak sources page on 2026-10-16; meaning inferred from its catalogued objects. |
| JPN | Japan | JP |  |
| KAZ | Kazakhstan | KZ |  |
| KEN | Republic of Kenya | KE |  |
| KWT | Kuwait | KW | Not on the CelesTrak sources page on 2026-10-16; meaning inferred from its catalogued objects. |
| LAOS | Laos | LA |  |
| LKA | Democratic Socialist Republic of Sri Lanka | LK |  |
| LTU | Lithuania | LT |  |
| LUXE | Luxembourg | LU |  |
| MA | Morroco | MA |  |
| MALA | Malaysia | MY |  |
| MCO | Principality of Monaco | MC |  |
| MDA | Republic of Moldova | MD |  |
| MEX | Mexico | MX |  |
| MMR | Republic of the Union of Myanmar | MM |  |
| MNE | Montenegro | ME |  |
| MNG | Mongolia | MN |  |
| MUS | Mauritius | MU |  |
| NATO | North Atlantic Treaty Organization | organization `nato` |  |
| NETH | Netherlands | NL |  |
| NICO | New ICO | organization `new-ico` |  |
| NIG | Nigeria | NG |  |
| NKOR | Democratic People's Republic of Korea | KP |  |
| NOR | Norway | NO |  |
| NPL | Federal Democratic Republic of Nepal | NP |  |
| NZ | New Zealand | NZ |  |
| O3B | O3b Networks | organization `o3b` |  |
| ORB | ORBCOMM | organization `orbcomm` |  |
| PAKI | Pakistan | PK |  |
| PERU | Peru | PE |  |
| POL | Poland | PL |  |
| POR | Portugal | PT |  |
| PRC | People's Republic of China | CN |  |
| PRES | People's Republic of China/European Space Agency | CN, organization `esa` |  |
| PRY | Republic of Paraguay | PY |  |
| QAT | State of Qatar | QA |  |
| RASC | RascomStar-QAF | organization `rascom` |  |
| ROC | Taiwan (Republic of China) | TW |  |
| ROM | Romania | RO |  |
| RP | Philippines (Republic of the Philippines) | PH |  |
| RWA | Republic of Rwanda | RW |  |
| SAFR | South Africa | ZA |  |
| SAUD | Saudi Arabia | SA |  |
| SDN | Republic of Sudan | SD |  |
| SEAL | Sea Launch | organization `sea-launch` |  |
| SEN | Republic of Senegal | SN |  |
| SES | SES | organization `ses` |  |
| SGJP | Singapore/Japan | SG, JP |  |
| SING | Singapore | SG |  |
| SKOR | Republic of Korea | KR |  |
| SLB | Solomon Islands | SB |  |
| SPN | Spain | ES |  |
| STCT | Singapore/Taiwan | SG, TW |  |
| SVK | Slovakia | SK | Not on the CelesTrak sources page on 2026-10-16; meaning inferred from its catalogued objects. |
| SVN | Slovenia | SI |  |
| SWED | Sweden | SE |  |
| SWTZ | Switzerland | CH |  |
| TBD | To Be Determined | unknown |  |
| THAI | Thailand | TH |  |
| TMMC | Turkmenistan/Monaco | TM, MC |  |
| TUN | Republic of Tunisia | TN |  |
| TURK | Türkiye | TR |  |
| UAE | United Arab Emirates | AE |  |
| UGA | Uganda | UG | Not on the CelesTrak sources page on 2026-10-16; meaning inferred from its catalogued objects. |
| UK | United Kingdom | GB |  |
| UKR | Ukraine | UA |  |
| UNK | Unknown | unknown |  |
| URY | Uruguay | UY |  |
| US | United States | US |  |
| USBZ | United States/Brazil | US, BR |  |
| VAT | Vatican City State | VA |  |
| VENZ | Venezuela | VE |  |
| VTNM | Vietnam | VN |  |
| ZWE | Republic of Zimbabwe | ZW |  |

## Other codes

| Namespace | Code | Label | Kind |
|---|---|---|---|
| ll2.agency_type | Government | Government | category |
| ll2.agency_type | Commercial | Commercial | category |
| ll2.agency_type | Private | Private | category |
| ll2.agency_type | Multinational | Multinational | category |
| ll2.agency_type | Educational | Educational | category |
| ll2.agency_type | Unknown | Unknown | unknown |
| ll2.country | ?? | Unknown | unknown |

## Countries

257 countries and territories with English and Japanese names from Unicode CLDR 48.2.3 (<https://raw.githubusercontent.com/unicode-org/cldr-json/48.2.3/cldr-json>).
