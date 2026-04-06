/**
 * db.ts — IndexedDB wrapper for local persistence.
 *
 * Stores chat history and projects in the browser's IndexedDB.
 * No server database needed — everything lives in the user's browser.
 *
 * IndexedDB is:
 *   - Built into every browser (Chrome, Firefox, Edge, Safari)
 *   - Persistent — survives tab close, browser restart, even OS restart
 *   - ~50MB-unlimited storage (browser-dependent)
 *   - Async (non-blocking)
 *
 * What we store:
 *   - Projects: {id, name, createdAt, dataContext, sessionId}
 *   - Messages: {id, projectId, role, content, createdAt}
 *
 * What we DON'T store (stays on server filesystem):
 *   - Actual CSV files (too large for IndexedDB)
 *   - Notebook .ipynb files
 */

const DB_NAME = "datapilot";
const DB_VERSION = 1;

export interface Project {
  id: string;
  name: string;
  sessionId: string;
  createdAt: string;
  dataContext: any;
  dataFileName?: string;
}

export interface ChatMessage {
  id: string;
  projectId: string;
  role: "user" | "assistant" | "code" | "thinking" | "error";
  content: string;
  createdAt: string;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;

      // Projects store
      if (!db.objectStoreNames.contains("projects")) {
        const store = db.createObjectStore("projects", { keyPath: "id" });
        store.createIndex("createdAt", "createdAt");
      }

      // Messages store
      if (!db.objectStoreNames.contains("messages")) {
        const store = db.createObjectStore("messages", { keyPath: "id" });
        store.createIndex("projectId", "projectId");
        store.createIndex("createdAt", "createdAt");
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// --- Projects ---

export async function saveProject(project: Project): Promise<void> {
  const db = await openDB();
  const tx = db.transaction("projects", "readwrite");
  tx.objectStore("projects").put(project);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getProject(id: string): Promise<Project | undefined> {
  const db = await openDB();
  const tx = db.transaction("projects", "readonly");
  const request = tx.objectStore("projects").get(id);
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function getAllProjects(): Promise<Project[]> {
  const db = await openDB();
  const tx = db.transaction("projects", "readonly");
  const request = tx.objectStore("projects").getAll();
  return new Promise((resolve, reject) => {
    request.onsuccess = () => {
      const projects = request.result as Project[];
      // Sort newest first
      projects.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
      resolve(projects);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function deleteProject(id: string): Promise<void> {
  const db = await openDB();
  const tx = db.transaction(["projects", "messages"], "readwrite");
  tx.objectStore("projects").delete(id);
  // Also delete all messages for this project
  const msgStore = tx.objectStore("messages");
  const index = msgStore.index("projectId");
  const request = index.openCursor(IDBKeyRange.only(id));
  request.onsuccess = () => {
    const cursor = request.result;
    if (cursor) {
      cursor.delete();
      cursor.continue();
    }
  };
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

// --- Messages ---

export async function saveMessage(message: ChatMessage): Promise<void> {
  const db = await openDB();
  const tx = db.transaction("messages", "readwrite");
  tx.objectStore("messages").put(message);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getMessages(projectId: string): Promise<ChatMessage[]> {
  const db = await openDB();
  const tx = db.transaction("messages", "readonly");
  const index = tx.objectStore("messages").index("projectId");
  const request = index.getAll(IDBKeyRange.only(projectId));
  return new Promise((resolve, reject) => {
    request.onsuccess = () => {
      const messages = request.result as ChatMessage[];
      messages.sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());
      resolve(messages);
    };
    request.onerror = () => reject(request.error);
  });
}
