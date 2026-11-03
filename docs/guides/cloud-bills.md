# Getting a bill from each cloud

CostPilot reads these files. All of them can be `.csv` or `.csv.gz`.

**Before you upload:** while the app uses a free Gemini key, please use made-up bills only. See `getting-started.md`.

| Cloud | File | Detail |
|---|---|---|
| Any cloud with FOCUS | FOCUS export | Line by line |
| AWS | Cost Explorer CSV, Cost and Usage Report, or FOCUS export | Cost Explorer has monthly totals only |
| Azure | Cost details export, actual cost | Line by line |
| Google Cloud | Standard billing export from BigQuery, using the query below | Line by line |
| Oracle Cloud | Cost report, either Oracle's own format or FOCUS | Line by line |
| DigitalOcean | Invoice CSV | Line by line |

**If a cloud offers FOCUS, use it.** It is the most standard choice, and AWS, Azure, Google Cloud and Oracle all offer it.

## Azure

In the Azure portal, go to **Cost Management**, then **Exports**, and create an export of **Cost and usage details (actual cost)**. Save the CSV file it creates.

- EA, Microsoft Customer Agreement and pay-as-you-go column names all work.
- Dates in month/day/year order are read correctly.
- Actual cost files do not spread reservations over the months they cover, so billed and effective cost are the same.

## Google Cloud

Google Cloud saves billing data in BigQuery. BigQuery cannot save nested credits to CSV, so use this query. It adds the credits for each row into one column.

```sql
SELECT
  billing_account_id,
  service.description AS service_description,
  sku.description AS sku_description,
  usage_start_time,
  usage_end_time,
  project.id AS project_id,
  location.region AS location_region,
  cost,
  currency,
  usage.amount AS usage_amount,
  usage.unit AS usage_unit,
  cost_type,
  cost_at_list,
  (SELECT SUM(c.amount) FROM UNNEST(credits) AS c) AS credits_total
FROM `YOUR_PROJECT.YOUR_DATASET.gcp_billing_export_v1_YOUR_ACCOUNT`
WHERE invoice.month = '202610'
```

Change the table name and month, then use **Save results** and choose **CSV**. Credits become their own records, so the totals match your invoice.

## Oracle Cloud

In the Console, go to **Billing & Cost Management**, then **Cost and Usage Reports**, and download a cost report. Both Oracle's own format and the FOCUS format work. Correction rows are kept as adjustments.

## DigitalOcean

Go to **Billing**, open an invoice, and download its CSV.

- The description column can hold IP addresses and server names. CostPilot stores it, but never sends it to the AI.
- DigitalOcean has no commitment discounts, so no recommendation rules are set for it yet.

## Checked against

The column names come from each cloud's official documentation, checked on 3 Nov 2026. No reader has been tested with a real bill from that cloud yet. If a real file is refused, the error names the row, so please report it.
