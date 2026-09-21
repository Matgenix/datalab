<template>
  <main class="container min-vh-100 d-flex align-items-center justify-content-center">
    <section class="text-center" aria-labelledby="magic-link-heading">
      <h1 id="magic-link-heading">Confirm magic link</h1>
      <form v-if="token" :action="magicLinkUrl" method="post">
        <p>Select Continue to use this magic link.</p>
        <input type="hidden" name="token" :value="token" />
        <button type="submit" class="btn btn-primary">Continue</button>
      </form>
      <p v-else class="alert alert-danger">No magic-link token was provided.</p>
    </section>
  </main>
</template>

<script>
import { API_URL } from "@/resources.js";

export default {
  props: {
    token: { type: String, default: "" },
  },
  data() {
    return {
      magicLinkUrl: `${API_URL}/login/email`,
    };
  },
};
</script>
