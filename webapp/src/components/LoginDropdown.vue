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
    v-if="showTestingUsernamePassword"
    type="button"
    class="dropdown-item btn login btn-link"
    aria-label="Login with username and password for testing only"
    style="background-color: #ff000062; white-space: normal"
    @click="testingUsernamePasswordLoginModalIsOpen = true"
  >
    Username/password
    <font-awesome-icon icon="exclamation-triangle" style="color: #b00020" />
    <span style="color: #b00020; font-size: 0.8rem; font-weight: 600; margin-left: 0.25rem"
      >for testing only</span
    >
  </button>
  <form
    v-if="showTestingUsernamePassword"
    class="modal-enclosure"
    @submit.prevent="submitTestingUsernamePasswordLogin"
  >
    <Modal
      v-model="testingUsernamePasswordLoginModalIsOpen"
      :disable-submit="testingUsernamePasswordLoginLoading || !testingUsername || !testingPassword"
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
          <label for="testing-username-password-login-username" class="col-form-label"
            >Username</label
          >
          <input
            id="testing-username-password-login-username"
            v-model="testingUsername"
            class="form-control"
            autocomplete="username"
            type="text"
          />
        </div>
        <div class="form-group">
          <label for="testing-username-password-login-password" class="col-form-label"
            >Password</label
          >
          <input
            id="testing-username-password-login-password"
            v-model="testingPassword"
            class="form-control"
            autocomplete="current-password"
            type="password"
          />
        </div>
        <div style="color: #b00020; font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem">
          Testing-only mechanism. Do not use this login path for production accounts.
        </div>
        <div v-if="testingUsernamePasswordLoginError" style="color: #b00020; font-size: 0.8rem">
          {{ testingUsernamePasswordLoginError }}
        </div>
      </template>
      <template #footer>
        <button
          type="submit"
          class="btn btn-info"
          :disabled="testingUsernamePasswordLoginLoading || !testingUsername || !testingPassword"
        >
          Login
        </button>
        <button
          type="button"
          class="btn btn-secondary"
          @click="testingUsernamePasswordLoginModalIsOpen = false"
        >
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
import { loginTestingUsernamePassword } from "@/server_fetch_utils.js";

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
      testingUsernamePasswordLoginModalIsOpen: false,
      testingUsername: "",
      testingPassword: "",
      testingUsernamePasswordLoginError: "",
      testingUsernamePasswordLoginLoading: false,
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
    showTestingUsernamePassword() {
      return (
        this.$store.state.serverInfo?.features?.auth_mechanisms?.testing_username_password ?? false
      );
    },
  },
  methods: {
    async submitTestingUsernamePasswordLogin() {
      this.testingUsernamePasswordLoginLoading = true;
      this.testingUsernamePasswordLoginError = "";
      try {
        const user = await loginTestingUsernamePassword(this.testingUsername, this.testingPassword);
        this.testingPassword = "";
        this.testingUsernamePasswordLoginModalIsOpen = false;
        this.$emit("current-user-changed", user);
      } catch {
        this.testingUsernamePasswordLoginError = "Login failed.";
      } finally {
        this.testingUsernamePasswordLoginLoading = false;
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
