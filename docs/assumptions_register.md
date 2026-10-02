# Assumptions & Parameter Provenance Register (PRD Rule R6 & Appendix D.3)

- **Registry Status**: `DEMO NOT READY (PLACEHOLDER PARAMETERS DETECTED)`
- **demo_ready**: `false`
- **Rule Enforcement**: Any economic parameter whose source status is `PLACEHOLDER` programmatically forces `demo_ready=false` and displays prominent farmer-facing disclaimers.

## Parameter Provenance Table

| Parameter                           | Value   | Unit                | Source Status               | Used In                   | Sensitivity                    | Owner to Verify               |
|:------------------------------------|:--------|:--------------------|:----------------------------|:--------------------------|:-------------------------------|:------------------------------|
| Tomato Spoilage Base Rate           | 5.0     | % weight loss / day | PLACEHOLDER                 | compute_spoilage_fraction | High (shifts holding horizon)  | ICAR / Field agronomist       |
| Tomato Storage Cost                 | 2.0     | ₹/quintal/day       | PLACEHOLDER                 | compute_storage_cost      | Medium (linear cost erosion)   | Mandi / FPO survey            |
| Tomato Loading & Handling Cost      | 10.0    | ₹/quintal           | PLACEHOLDER                 | compute_transport_cost    | Low (fixed terminal cost)      | Transporter field survey      |
| Tomato Transport Rate (tempo)       | 18.0    | ₹/km (trip-based)   | PLACEHOLDER                 | compute_transport_cost    | High (scales with distance)    | RTO / Transport union rates   |
| Tomato Transport Rate (truck)       | 28.0    | ₹/km (trip-based)   | PLACEHOLDER                 | compute_transport_cost    | High (scales with distance)    | RTO / Transport union rates   |
| Tomato Farmer Mandi Commission      | 0.0%    | % of gross revenue  | MH_APMC_Act_Sec32_Verified  | compute_fees              | High (statutory deduction)     | State APMC Act (Verified)     |
| Tomato Weighing & Hamali Charge     | 2.0     | ₹/quintal           | MH_APMC_Act_Sec32_Verified  | compute_fees              | Low (statutory flat fee)       | APMC Gazette Notification     |
| Onion Spoilage Base Rate            | 0.8     | % weight loss / day | PLACEHOLDER                 | compute_spoilage_fraction | High (shifts holding horizon)  | ICAR / Field agronomist       |
| Onion Storage Cost                  | 1.2     | ₹/quintal/day       | PLACEHOLDER                 | compute_storage_cost      | Medium (linear cost erosion)   | Mandi / FPO survey            |
| Onion Loading & Handling Cost       | 10.0    | ₹/quintal           | PLACEHOLDER                 | compute_transport_cost    | Low (fixed terminal cost)      | Transporter field survey      |
| Onion Transport Rate (tempo)        | 16.0    | ₹/km (trip-based)   | PLACEHOLDER                 | compute_transport_cost    | High (scales with distance)    | RTO / Transport union rates   |
| Onion Transport Rate (truck)        | 26.0    | ₹/km (trip-based)   | PLACEHOLDER                 | compute_transport_cost    | High (scales with distance)    | RTO / Transport union rates   |
| Onion Farmer Mandi Commission       | 0.0%    | % of gross revenue  | MH_APMC_Act_Sec32_Verified  | compute_fees              | High (statutory deduction)     | State APMC Act (Verified)     |
| Onion Weighing & Hamali Charge      | 2.0     | ₹/quintal           | MH_APMC_Act_Sec32_Verified  | compute_fees              | Low (statutory flat fee)       | APMC Gazette Notification     |
| Soybean Spoilage Base Rate          | 0.05    | % weight loss / day | PLACEHOLDER                 | compute_spoilage_fraction | High (shifts holding horizon)  | ICAR / Field agronomist       |
| Soybean Storage Cost                | 0.8     | ₹/quintal/day       | PLACEHOLDER                 | compute_storage_cost      | Medium (linear cost erosion)   | Mandi / FPO survey            |
| Soybean Loading & Handling Cost     | 10.0    | ₹/quintal           | PLACEHOLDER                 | compute_transport_cost    | Low (fixed terminal cost)      | Transporter field survey      |
| Soybean Transport Rate (tempo)      | 15.0    | ₹/km (trip-based)   | PLACEHOLDER                 | compute_transport_cost    | High (scales with distance)    | RTO / Transport union rates   |
| Soybean Transport Rate (truck)      | 25.0    | ₹/km (trip-based)   | PLACEHOLDER                 | compute_transport_cost    | High (scales with distance)    | RTO / Transport union rates   |
| Soybean Farmer Mandi Commission     | 0.0%    | % of gross revenue  | MP_Mandi_Adhiniyam_Verified | compute_fees              | High (statutory deduction)     | State APMC Act (Verified)     |
| Soybean Weighing & Hamali Charge    | 2.5     | ₹/quintal           | MP_Mandi_Adhiniyam_Verified | compute_fees              | Low (statutory flat fee)       | APMC Gazette Notification     |
| Soybean Minimum Support Price (MSP) | 4892.0  | ₹/quintal           | CCEA_MSP_2024_Verified      | baseline comparison       | Medium (price floor reference) | CCEA Kharif/Rabi Notification |
