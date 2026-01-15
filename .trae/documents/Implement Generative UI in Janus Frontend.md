I will implement the **Generative UI** feature in the Janus frontend using Angular Dynamic Components, enabling the interface to render visual components (like tables) based on structured data embedded in chat messages.

### **Plan: Generative UI Implementation**

1.  **Create Generative UI Components** (`front/src/app/features/chat/generative-ui/`)
    *   **`GenTableComponent`**: A component that accepts `columns` and `data` inputs to render a dynamic table.
    *   **`DynamicHostComponent`**: A wrapper component using `ViewContainerRef` to dynamically instantiate and render specific UI components (like `GenTableComponent`) based on a `type` input.

2.  **Update Data Models**
    *   Modify `ChatMessage` interface in `front/src/app/services/janus-api.service.ts` to include an optional `ui` field: `ui?: { type: string; data: any; }`.

3.  **Enhance `ChatComponent` Logic** (`front/src/app/features/chat/chat/chat.ts`)
    *   Implement a `parseUiElements(text: string)` method to detect and extract `<janus-ui type="...">JSON_DATA</janus-ui>` tags from message text.
    *   Update `loadChat` and `sendMessage` (handling responses) to process messages through this parser, separating the UI configuration from the text content.
    *   Register `DynamicHostComponent` in the component imports.

4.  **Update Chat Template** (`front/src/app/features/chat/chat/chat.html`)
    *   Insert the `<app-dynamic-host>` component within the message loop, conditioned on the presence of the `ui` field in the message object.

5.  **Verification**
    *   I will inject a test message with a `<janus-ui>` tag into the chat stream to verify that the table renders correctly alongside the text.

### **Technical Details**
*   **Tag Syntax**: `<janus-ui type="table">{"columns": ["Name", "Role"], "data": [{"Name": "Janus", "Role": "AI"}]}</janus-ui>`
*   **Dynamic Loading**: Uses Angular's `createComponent` API to load components without needing a complex router configuration for them.
