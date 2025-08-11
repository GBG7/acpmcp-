// src/interfaces/interfaces.ts
export interface message {
  id: string;
  role: "user" | "assistant";
  content?: string;   // text is optional (image-only messages won't have it)
  imgSrc?: string;    // image data URI 
}
