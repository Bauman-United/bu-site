"use server";

import { PARTNER_FORM, type PartnerState, partnerValuesFromForm } from "@/lib/partners";
import { postForm } from "@/lib/submit-form";

export async function submitPartner(_prev: PartnerState, formData: FormData): Promise<PartnerState> {
  return postForm("/partners", PARTNER_FORM, partnerValuesFromForm(formData));
}
