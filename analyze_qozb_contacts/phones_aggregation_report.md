# QOZB Phones Aggregation Analysis

This report analyzes the phone number aggregation in the QOZB dataset, mirroring the logic used in the `/admin/prospects` page of `oz-dev-dash`.

**Dataset**: QOZB Development Projects CSV
**Total Rows (Properties)**: 21287
**Total Unique Phones found**: 24920

## Aggregation Stats

In the CRM UI, a single phone number represents a "Communication Channel", which is linked to potentially multiple properties, entities, and contacts.

- **Phones linked to 1 Property**: 20157
- **Phones linked to >1 Properties**: 4763
- **Phones linking >1 distinct Entity names**: 16213

### Top 10 Phones by Property Count (Highly Aggregated)
- **Not Available**: 1512 properties
  - Entities: ['Larson, David A.', 'Prospera Property Management', 'Silberstein, Abraham']
  - Contacts: ['Patel Pratikkumar', 'Cathy Fontana', 'Bradley Johnson']
- **2144142564**: 341 properties
  - Entities: ['Spruce Capital Partners', 'KJAX Property', 'Continental Property Services']
  - Contacts: ['RJ Socci', 'Melissa White', 'Jeff Gray']
- **2027159500**: 266 properties
  - Entities: ['Independence Realty Trust', 'KJAX Property', 'Tablerock Capital']
  - Contacts: ['Zach Haptonstall', 'Patel Pratikkumar', 'Ivana Christman']
- **7137825800**: 205 properties
  - Entities: ['Kairos Investment Management', 'Prime Capital Investments', 'LRC Commercial']
  - Contacts: ['Aaron Goldklang', 'Brian Hanson', 'Rodrick L. Schmidt']
- **9163575300**: 154 properties
  - Entities: ['Tides Equities', 'AOF/Pacific Affordable Housing', 'Oakmont Properties']
  - Contacts: ['Brian Hanson', 'April Black', 'Cynthia Hobbs']
- **5713823700**: 137 properties
  - Entities: ['Beacon Management - MI', 'Spark Management', 'Knightvest Capital']
  - Contacts: ['Raymond Safi', 'Melissa White', 'Bryan Taing']
- **6177424500**: 134 properties
  - Entities: ['Standard Communities', 'Becker + Becker', 'White Plains Housing Authority']
  - Contacts: ['Patrick M. Appleby', 'David Cooke', 'David R. McCarthy']
- **2487233110**: 122 properties
  - Entities: ['MC Companies', 'Edison47', 'Gates Hudson']
  - Contacts: ['Melissa White', 'Scott Walker', 'Bradley Johnson']
- **3033089000**: 97 properties
  - Entities: ['Sunset Group', 'KeyCorp Real Estate Capital Markets', 'Eaton Vance Real Estate Investment Group']
  - Contacts: ['Brian Hanson', 'Charlie Keels', 'Nathan D. Shipp']
- **7037141401**: 97 properties
  - Entities: ['Goldman Sachs & Company', 'Carmel Partners', 'Greystar Management']
  - Contacts: ['Norman Jemal', 'Brian Hanson', 'Joseph A. Panepinto']
