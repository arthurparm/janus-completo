Implemented the **Generative UI** feature in the Janus frontend using Angular dynamic components so chat messages can render structured UI blocks (like tables).

### **Implementation Summary**

1. **Generative UI Components** (`front/src/app/features/chat/generative-ui/`)

   * **`GenTableComponent`**: Renders dynamic tables from structured payloads.
   * **`DynamicHostComponent`**: Instantiates supported UI components based on `type`.

2. **Data Model**

   * `ChatMessage` now supports `ui?: { type: string; data: any; }` in `front/src/app/services/janus-api.service.ts`.

3. **Chat Parsing + Wiring** (`front/src/app/features/chat/chat/chat.ts`)

   * `parseUiElements(text: string)` extracts `<janus-ui>` blocks and separates text from UI config.
   * `loadChat` and `sendMessage` route parsed data to the UI host.
   * `DynamicHostComponent` is registered in the chat component imports.

4. **Chat Template** (`front/src/app/features/chat/chat/chat.html`)

   * `<app-dynamic-host>` renders inside the message loop when `msg.ui` is present.

### **Supported Payloads**

* **Tag Syntax**:
  `<janus-ui type="table">{"columns": ["Name", "Role"], "data": [{"Name": "Janus", "Role": "AI"}]}</janus-ui>`

* **Table Payload (accepted shapes)**:
  * `{ "columns": ["Name", "Role"], "data": [ { "Name": "Janus", "Role": "AI" } ] }`
  * `{ "columns": [ { "header": "Name", "key": "name" } ], "rows": [ { "name": "Janus" } ] }`
  * If `columns` is missing, it is inferred from the first row.

### **Verification**

* Paste a message with a `<janus-ui>` tag into chat and confirm the table renders under the response text.
