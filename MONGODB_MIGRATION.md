# MongoDB Migration Schema Documentation

Migrating from SQLite to MongoDB allows for better scalability, flexible metadata storage, and native handling of high-frequency telemetry data.

## 🍃 Collection Strategies

### 1. `users` Collection
Stores user profiles and authentication data.
```json
{
  "_id": "rohith.p@lyzr.ai",        // String (username)
  "password": "$2b$12$...",        // Bcrypt Hash
  "current_session_id": "uuid-...", // Last active chat session
  "role": "admin",                 // Access control (admin/user)
  "created_at": ISODate("...")
}
```
**Indexes**:
- `_id`: Primary Key

### 2. `traces` Collection
Stores interaction logs. MongoDB's flexible schema is ideal here as Lyzr may add more fields in the future without requiring a migration.
```json
{
  "_id": "trace_67890",            // String (Lyzr Trace ID)
  "user_id": "username@email.com", // Indexed for fast lookups
  "agent_id": "Specialist_Agent",  // Indexed for filtering
  "session_id": "uuid-...",        // Link to specific conversation
  "credits": 0.045,                // Decimal/Double
  "created_at": ISODate("..."),    // Date object (Native filtering)
  "payload": {                     // Flexible object for raw API data
    "input": "User query text",
    "output": "Agent response text",
    "inspect_url": "https://..."
  },
  "metadata": {                    // Optional: for future expansion
     "tokens": 450,
     "version": "v3"
  }
}
```
**Indexes**:
- `user_id`: 1
- `agent_id`: 1
- `created_at`: -1 (Descending for dashboard)
- `user_id_1_agent_id_1`: Compound index for admin filtering

### 3. `trace_mappings` Collection
Acts as a temporary buffer for fuzzy attribution.
```json
{
  "_id": "interaction_uuid_123",   // Local UUID sent in chat payload
  "user_id": "username@email.com",
  "session_id": "uuid-...",
  "created_at": ISODate("...")     // Use TTL index to auto-clear old mappings
}
```
**Optimizations**:
- **TTL Index**: Set `expireAfterSeconds: 86400` (24h) to automatically prune old mappings.

### 4. `settings` Collection
Global key-value configuration.
```json
{
  "_id": "max_credits",            // Setting Key
  "value": 2.0,                    // Setting Value
  "updated_at": ISODate("...")
}
```

---

## �️ Step-by-Step Migration Execution Plan

This plan outlines the 5 phases to move from SQLite to MongoDB Atlas or a local instance.

### Phase 1: Environment & Connectivity
1.  **Install Dependencies**:
    ```bash
    pip install "pymongo[srv]" dns构
    ```
2.  **Add Environment Variables**:
    Update your `.env` file:
    ```env
    MONGO_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
    MONGO_DB_NAME=lyzr_assistant
    ```

### Phase 2: Database Abstraction Layer
1.  Create `database_manager.py`:
    *   Initialize a `MongoClient` using the `MONGO_URI`.
    *   Create helper functions that mirror the signature of `auth.py` functions (e.g., `get_user`, `save_trace`).
    *   This ensures `app.py` doesn't need a total rewrite.

### Phase 3: Data Migration Script
1.  Create a `migrate_data.py` script to perform a one-time transfer:
    *   Read all rows from `users.db` using `sqlite3`.
    *   Transform the rows into the JSON format defined in the schema above.
    *   Use `insert_many()` to push data into MongoDB collections.
    *   **Verification**: Compare document counts between SQLite and MongoDB.

### Phase 4: Application Logic Swap
1.  **Refactor `auth.py`**:
    *   Replace `sqlite3` imports with `from database_manager import db`.
    *   Update `verify_user`, `create_user`, and `save_traces_bulk` to use MongoDB collections (`db.users.find_one(...)`, etc.).
    *   Implement **Indexes**: Ensure unique index on `username` in the `users` collection.

### Phase 5: Testing & Deployment
1.  **Local Validation**: Run the Streamlit app and verify:
    *   Login/Signup still work.
    *   Historical traces are visible in the Dashboard.
    *   Settings are preserved.
2.  **Cutover**: Switch production environment to the new Mongo-enabled codebase.
3.  **Cleanup**: Delete the local `users.db` once MongoDB is fully verified.

---
**💡 Pro Tip**: During the transition, you can keep both databases running in parallel (Double Writing) for a few days to ensure stability before fully cutting off SQLite.
