"use server";

import { JOIN_FORM, type JoinState, valuesFromForm } from "@/lib/join";
import { postForm } from "@/lib/submit-form";

export async function submitJoin(_prev: JoinState, formData: FormData): Promise<JoinState> {
  return postForm("/join", JOIN_FORM, valuesFromForm(formData));
}
