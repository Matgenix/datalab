<template>
  <GetEmailModal v-model="emailModalIsOpen" />
  <span v-if="!authMechanismsLoaded" class="dropdown-item text-muted">
    <font-awesome-icon :icon="['fa', 'spinner']" spin /> Loading…
  </span>
  <a
    v-if="showGitHub"
    type="button"
    class="dropdown-item btn login btn-link"
    aria-label="Login via GitHub"
    :href="apiUrl + '/login/github'"
    ><font-awesome-icon :icon="['fab', 'github']" /> Login via GitHub</a
  >
  <a
    v-if="showORCID"
    type="button"
    class="dropdown-item btn login btn-link"
    aria-label="Login via ORCID"
    :href="apiUrl + '/login/orcid'"
    ><font-awesome-icon class="orcid-icon" :icon="['fab', 'orcid']" /> Login via ORCID</a
  >
  <a
    v-if="showGoogle"
    type="button"
    class="dropdown-item btn login btn-link"
    aria-label="Login via Google"
    :href="apiUrl + '/login/google'"
    ><font-awesome-icon :icon="['fab', 'google']" /> Login via Google</a
  >
  <a
    v-if="showMicrosoft"
    type="button"
    class="dropdown-item btn login btn-link"
    aria-label="Login via Microsoft"
    :href="apiUrl + '/login/microsoft'"
    ><font-awesome-icon :icon="['fab', 'microsoft']" /> Login via Microsoft</a
  >
  <button
    v-if="showEmail"
    type="button"
    class="dropdown-item btn login btn-link"
    aria-label="Login via email"
    @click="emailModalIsOpen = true"
  >
    <font-awesome-icon :icon="['fa', 'envelope']" /> Login via email
  </button>
  <button
    v-if="showLocal"
    type="button"
    class="dropdown-item btn login btn-link"
    aria-label="Login with username and password for testing only"
    style="background-color: #ff000062; white-space: normal"
    @click="localLoginModalIsOpen = true"
  >
    Username/password
    <font-awesome-icon icon="exclamation-triangle" style="color: #b00020" />
    <span style="color: #b00020; font-size: 0.8rem; font-weight: 600; margin-left: 0.25rem"
      >for testing only</span
    >
  </button>
  <form v-if="showLocal" class="modal-enclosure" @submit.prevent="submitLocalLogin">
    <Modal
      v-model="localLoginModalIsOpen"
      :disable-submit="localLoginLoading || !localUsername || !localPassword"
      :is-large="false"
    >
      <template #header>
        <font-awesome-icon icon="exclamation-triangle" style="color: #b00020" />
        Username/password login
      </template>
      <template #body>
        <div class="alert alert-warning" style="border-color: #b00020">
          <font-awesome-icon icon="exclamation-triangle" style="color: #b00020" />
          This username/password login is for testing only.
        </div>
        <div class="form-group">
          <label for="local-login-username" class="col-form-label">Username</label>
          <input
            id="local-login-username"
            v-model="localUsername"
            class="form-control"
            autocomplete="username"
            type="text"
          />
        </div>
        <div class="form-group">
          <label for="local-login-password" class="col-form-label">Password</label>
          <input
            id="local-login-password"
            v-model="localPassword"
            class="form-control"
            autocomplete="current-password"
            type="password"
          />
        </div>
        <div style="color: #b00020; font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem">
          Testing-only mechanism. Do not use this login path for production accounts.
        </div>
        <div v-if="localLoginError" style="color: #b00020; font-size: 0.8rem">
          {{ localLoginError }}
        </div>
      </template>
      <template #footer>
        <button
          type="submit"
          class="btn btn-info"
          :disabled="localLoginLoading || !localUsername || !localPassword"
        >
          Login
        </button>
        <button type="button" class="btn btn-secondary" @click="localLoginModalIsOpen = false">
          Close
        </button>
      </template>
    </Modal>
  </form>
</template>

<script>
import GetEmailModal from "@/components/GetEmailModal.vue";
import Modal from "@/components/Modal.vue";
import { API_URL } from "@/resources.js";
import { loginLocal } from "@/server_fetch_utils.js";

export default {
  components: {
    GetEmailModal,
    Modal,
  },
  props: {
    modelValue: Boolean,
  },
  emits: ["current-user-changed"],
  data() {
    return {
      emailModalIsOpen: false,
      apiUrl: API_URL,
      localLoginModalIsOpen: false,
      localUsername: "",
      localPassword: "",
      localLoginError: "",
      localLoginLoading: false,
    };
  },
  computed: {
    authMechanismsLoaded() {
      return this.$store.state.serverInfo?.features?.auth_mechanisms != null;
    },
    showGitHub() {
      return this.$store.state.serverInfo?.features?.auth_mechanisms?.github ?? false;
    },
    showORCID() {
      return this.$store.state.serverInfo?.features?.auth_mechanisms?.orcid ?? false;
    },
    showGoogle() {
      return this.$store.state.serverInfo?.features?.auth_mechanisms?.google ?? false;
    },
    showMicrosoft() {
      return this.$store.state.serverInfo?.features?.auth_mechanisms?.microsoft ?? false;
    },
    showEmail() {
      return this.$store.state.serverInfo?.features?.auth_mechanisms?.email ?? false;
    },
    showLocal() {
      return this.$store.state.serverInfo?.features?.auth_mechanisms?.testing_local ?? false;
    },
  },
  methods: {
    async submitLocalLogin() {
      this.localLoginLoading = true;
      this.localLoginError = "";
      try {
        const user = await loginLocal(this.localUsername, this.localPassword);
        this.localPassword = "";
        this.localLoginModalIsOpen = false;
        this.$emit("current-user-changed", user);
      } catch {
        this.localLoginError = "Login failed.";
      } finally {
        this.localLoginLoading = false;
      }
    },
  },
};
</script>

<style scoped>
.btn:disabled {
  cursor: not-allowed;
}

.user-display-name {
  font-weight: bold;
}

.orcid-icon {
  color: #a6ce39;
}
</style>
