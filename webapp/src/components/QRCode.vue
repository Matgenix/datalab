<template>
  <div class="text-center">
    <a :href="currentQRCodeUrl" target="_blank" rel="noopener noreferrer">
      <img :src="qrCode.image" :width="width" :height="width" alt="QR code" />
    </a>

    <div
      id="qrcode-text-label"
      :style="{ width: width }"
      class="qrcode-text-label mx-auto text-center center-text"
    >
      {{ refcode }}
    </div>

    <div class="mt-2">
      <span v-if="!isPublicMode" class="badge bg-primary text-light">Private QR Code</span>
      <span v-else class="badge bg-warning text-dark">Public QR Code</span>
    </div>

    <div class="shareable-link mt-2 d-flex align-items-center" data-testid="shareable-link">
      <a
        :href="currentQRCodeUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="text-truncate small flex-grow-1"
      >
        {{ currentQRCodeUrl }}
      </a>
      <button
        type="button"
        class="btn btn-link btn-sm p-0 flex-shrink-0 ms-3"
        :aria-label="copied ? 'Link copied to clipboard' : 'Copy shareable link to clipboard'"
        @click="copyUrl"
      >
        <font-awesome-icon :icon="copied ? 'check' : 'copy'" />
      </button>
    </div>

    <div class="label-printing mt-3" data-testid="label-printing">
      <label for="label-profile" class="form-label">Label format</label>
      <select
        id="label-profile"
        class="form-select"
        :value="selectedProfile.id"
        @change="selectLabelProfile"
      >
        <option v-for="profile in labelProfiles" :key="profile.id" :value="profile.id">
          {{ profile.name }}
        </option>
      </select>
      <div class="label-preview mx-auto my-2" :style="previewPageStyle">
        <div :style="previewContentStyle">
          <img :src="qrCode.image" :style="previewQRStyle" alt="QR label preview" />
          <div>{{ refcode }}</div>
        </div>
      </div>
      <div v-if="qrTooDense" class="alert alert-warning py-2" data-testid="qr-density-warning">
        This QR code may be unreliable at this label size ({{ moduleDots }} printer dots per
        module).
      </div>
      <small class="d-block text-muted mb-2">
        In the print dialog, use matching media, 100% scale, no margins, and no headers or footers.
      </small>
      <button type="button" class="btn btn-info" @click="printLabel">
        {{ qrTooDense ? "Print anyway" : "Print label" }}
      </button>
    </div>
  </div>

  <div v-if="isLoading" class="text-center mt-3">
    <div class="spinner-border spinner-border-sm" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
    <small class="d-block mt-1">Checking existing tokens...</small>
  </div>

  <div v-if="!isPublicMode" class="mt-3">
    <div class="alert alert-info">
      <strong v-if="hasExistingToken">Public QR Code Exists:</strong>
      <strong v-else>Generate Public QR Code:</strong>
      <br />
      <span v-if="hasExistingToken">
        A public QR code already exists for this item. You can generate a new token. Both tokens
        will remain valid until manually revoked by an administrator.
      </span>
      <span v-else>
        This QR code requires authentication to access. You can generate a public QR code that
        allows access without login.
      </span>
    </div>

    <button
      class="btn btn-warning w-100"
      :disabled="isGenerating"
      @click.prevent="generatePublicQRCode()"
    >
      <span v-if="isGenerating">
        <span class="spinner-border spinner-border-sm me-2" role="status"></span>
        Generating...
      </span>
      <span v-else-if="hasExistingToken"> <i class="fas fa-plus me-2"></i>Generate New Token </span>
      <span v-else> <i class="fas fa-unlock me-2"></i>Generate Public QR Code </span>
    </button>
  </div>

  <div v-else class="mt-3">
    <div class="alert alert-warning">
      <strong><i class="fas fa-exclamation-triangle me-2"></i>Public QR Code Active</strong><br />
      This QR code can be accessed by anyone with the link. No authentication required.
      <div class="mt-2">
        <small><strong>Created:</strong> {{ formattedCreationDate }}</small>
      </div>
    </div>

    <button
      class="btn btn-danger w-100"
      :disabled="isInvalidating"
      @click.stop.prevent="invalidateToken"
    >
      <span v-if="isInvalidating">
        <span class="spinner-border spinner-border-sm me-2" role="status"></span>
        Deleting...
      </span>
      <span v-else> <i class="fas fa-trash me-1"></i>Delete Token </span>
    </button>
  </div>

  <div v-if="errorMessage" class="alert alert-danger mt-3">
    <i class="fas fa-exclamation-triangle me-2"></i>{{ errorMessage }}
  </div>

  <div v-if="!federatedQR" class="alert alert-info mt-3">
    QR_CODE_RESOLVER_URL is not set to the federation resolver URL for this deployment.<br />
    Links embedded within QR codes generated here will only work if this <i>datalab</i> instance
    remains at the same URL.<br /><br />

    Visit <a :href="federationQRCodeUrl">{{ federationQRCodeUrl }}</a> to learn about persistent URL
    resolution in <i>datalab</i>.
  </div>
</template>

<script>
import { DialogService } from "@/services/DialogService";
import { BUILTIN_LABEL_PROFILES, dotsPerModule, makeQRCode } from "@/label_printing.js";

import { FEDERATION_QR_CODE_RESOLVER_URL, QR_CODE_RESOLVER_URL, API_URL } from "@/resources.js";

export default {
  name: "QRCode",
  props: {
    refcode: {
      type: String,
      required: true,
    },
    width: {
      type: Number,
      default: 200,
    },
  },
  emits: ["public-token-generated", "public-token-invalidated"],
  data() {
    return {
      federationQRCodeUrl: FEDERATION_QR_CODE_RESOLVER_URL,
      isPublicMode: false,
      publicToken: null,
      tokenInfo: null,
      isLoading: false,
      isGenerating: false,
      isInvalidating: false,
      errorMessage: null,
      copied: false,
      selectedProfileId: null,
    };
  },
  computed: {
    federatedQR() {
      return FEDERATION_QR_CODE_RESOLVER_URL == QR_CODE_RESOLVER_URL;
    },
    privateQRCodeUrl() {
      if (QR_CODE_RESOLVER_URL == null) {
        return API_URL + "/items/" + this.refcode + "?redirect-to-ui=true";
      }
      return QR_CODE_RESOLVER_URL + "/" + this.refcode;
    },
    publicQRCodeUrl() {
      if (!this.publicToken) return this.privateQRCodeUrl;

      if (QR_CODE_RESOLVER_URL == null) {
        return `${API_URL}/items/${this.refcode}?redirect-to-ui=true&at=${this.publicToken}`;
      }
      return `${QR_CODE_RESOLVER_URL}/${this.refcode}?at=${this.publicToken}`;
    },
    currentQRCodeUrl() {
      const url = this.isPublicMode ? this.publicQRCodeUrl : this.privateQRCodeUrl;
      return url;
    },
    qrCode() {
      return makeQRCode(this.currentQRCodeUrl);
    },
    labelProfiles() {
      return [
        ...BUILTIN_LABEL_PROFILES,
        ...(this.$store.state.serverInfo?.label_printing?.profiles || []),
      ];
    },
    selectedProfile() {
      const configured = this.$store.state.serverInfo?.label_printing?.default_profile;
      const preferred =
        this.selectedProfileId || localStorage.getItem("datalab-label-profile") || configured;
      return (
        this.labelProfiles.find(({ id }) => id === preferred) ||
        BUILTIN_LABEL_PROFILES.find(({ id }) => id === "a4-single")
      );
    },
    moduleDots() {
      return dotsPerModule(this.selectedProfile, this.qrCode.modules);
    },
    qrTooDense() {
      return this.moduleDots < this.selectedProfile.min_module_dots;
    },
    labelHeightMm() {
      return this.selectedProfile.height_mm || this.selectedProfile.max_qr_size_mm + 10;
    },
    previewPageStyle() {
      const scale = Math.min(240 / this.selectedProfile.width_mm, 160 / this.labelHeightMm);
      return {
        width: `${this.selectedProfile.width_mm * scale}px`,
        height: `${this.labelHeightMm * scale}px`,
      };
    },
    previewContentStyle() {
      const sideMargin =
        (this.selectedProfile.width_mm - this.selectedProfile.printable_width_mm) / 2;
      const topMargin = this.selectedProfile.height_mm
        ? (this.selectedProfile.height_mm - this.selectedProfile.printable_height_mm) / 2
        : 1;
      return {
        width: `${(this.selectedProfile.max_qr_size_mm / this.selectedProfile.width_mm) * 100}%`,
        marginTop: `${(topMargin / this.labelHeightMm) * 100}%`,
        marginLeft:
          this.selectedProfile.alignment === "center"
            ? "auto"
            : `${(sideMargin / this.selectedProfile.width_mm) * 100}%`,
        marginRight: this.selectedProfile.alignment === "center" ? "auto" : "0",
        textAlign: "center",
      };
    },
    previewQRStyle() {
      return { width: "100%" };
    },
    formattedCreationDate() {
      if (!this.tokenInfo?.created_at) return "Unknown";

      try {
        const date = new Date(this.tokenInfo.created_at);
        return date.toLocaleDateString() + " at " + date.toLocaleTimeString();
      } catch {
        return "Unknown";
      }
    },
    hasExistingToken() {
      return this.tokenInfo && this.publicToken === "existing-token";
    },
  },
  mounted() {
    this.checkExistingToken();
  },
  beforeUnmount() {
    this.errorMessage = null;
  },
  methods: {
    selectLabelProfile(event) {
      this.selectedProfileId = event.target.value;
      localStorage.setItem("datalab-label-profile", this.selectedProfileId);
    },
    printLabel() {
      const profile = this.selectedProfile;
      const sideMargin = (profile.width_mm - profile.printable_width_mm) / 2;
      const topMargin = profile.height_mm
        ? (profile.height_mm - profile.printable_height_mm) / 2
        : 1;
      const contentMargin = profile.alignment === "center" ? "auto" : "0";
      const label = document.createElement("div");
      const section = document.createElement("section");
      const image = document.createElement("img");
      const identifier = document.createElement("div");
      const style = document.createElement("style");
      label.className = "qr-label-print";
      image.src = this.qrCode.image;
      image.alt = "QR code";
      identifier.textContent = this.refcode;
      section.append(image, identifier);
      label.append(section);
      style.textContent = `
        @page { size: ${profile.width_mm}mm ${this.labelHeightMm}mm; margin: 0; }
        @media print {
          body { margin: 0; }
          body > * { display: none !important; }
          body > .qr-label-print { display: block !important; width: ${profile.printable_width_mm}mm; margin-left: ${sideMargin}mm; padding-top: ${topMargin}mm; }
          .qr-label-print section { width: ${profile.max_qr_size_mm}mm; margin: 0 ${contentMargin}; text-align: center; }
          .qr-label-print img { display: block; width: ${profile.max_qr_size_mm}mm; height: ${profile.max_qr_size_mm}mm; }
          .qr-label-print div { margin-top: 1mm; font: 2mm/2.4mm monospace; overflow-wrap: anywhere; }
        }`;
      document.body.append(style, label);
      window.addEventListener(
        "afterprint",
        () => {
          label.remove();
          style.remove();
        },
        { once: true },
      );
      window.print();
    },
    async copyUrl() {
      await navigator.clipboard.writeText(this.currentQRCodeUrl);
      this.copied = true;
      setTimeout(() => {
        this.copied = false;
      }, 1500);
    },
    async checkExistingToken() {
      this.isLoading = true;
      this.errorMessage = null;

      const urlParams = new URLSearchParams(window.location.search);
      const accessToken = urlParams.get("at");
      if (accessToken) {
        this.isLoading = false;
        return;
      }

      try {
        const response = await fetch(`${API_URL}/items/${this.refcode}/access-token-info`, {
          method: "GET",
          credentials: "include",
        });

        const data = await response.json();

        if (response.ok && data.status === "success") {
          if (data.has_token) {
            this.tokenInfo = data.token_info;
            this.publicToken = "existing-token";
          }
        } else if (response.status === 404) {
          console.debug("No access to item or item not found");
        } else {
          console.warn("Error checking token:", data.message);
        }
      } catch (error) {
        console.error("Error checking existing token:", error);
      } finally {
        this.isLoading = false;
      }
    },
    async generatePublicQRCode() {
      setTimeout(async () => {
        const confirmationMessage = this.hasExistingToken
          ? "This will generate a new public QR code. The old token will remain valid until manually revoked by an administrator. Are you sure you want to proceed?"
          : "This will create a QR code that can be accessed by anyone without authentication. Are you sure you want to proceed?";

        const confirmed = await DialogService.confirm({
          title: this.hasExistingToken ? "Generate New Public QR Code" : "Generate Public QR Code",
          message: confirmationMessage,
          type: "warning",
          confirmButtonText: this.hasExistingToken
            ? "Generate New Token"
            : "Generate Public QR Code",
          cancelButtonText: "Cancel",
        });

        if (!confirmed) {
          return;
        }

        this.isGenerating = true;

        try {
          const response = await fetch(`${API_URL}/items/${this.refcode}/issue-access-token`, {
            method: "POST",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
            },
          });

          const data = await response.json();

          if (response.ok && data.status === "success") {
            this.publicToken = data.token;
            this.isPublicMode = true;
            this.tokenInfo = {
              created_at: new Date().toISOString(),
              created_by: this.$store.state.currentUserID,
            };
            this.$emit("public-token-generated", {
              refcode: this.refcode,
              token: data.token,
            });
          } else {
            throw new Error(data.message || "Failed to generate access token");
          }
        } catch (error) {
          console.error("Error generating public QR code:", error);
          this.errorMessage = `Failed to generate public QR code: ${error.message}`;
        } finally {
          this.isGenerating = false;
        }
      }, 100);
    },
    async invalidateToken() {
      const confirmed = await DialogService.confirm({
        title: "Delete Public QR Code",
        message:
          "This will permanently invalidate the public QR code. Anyone with the current link will no longer be able to access this item. Are you sure?",
        type: "warning",
        confirmButtonText: "Delete Token",
        cancelButtonText: "Cancel",
      });

      if (!confirmed) {
        return;
      }

      this.isInvalidating = true;
      this.errorMessage = null;

      try {
        const response = await fetch(`${API_URL}/items/${this.refcode}/invalidate-access-token`, {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({}),
        });

        const data = await response.json();

        if (response.ok && data.status === "success") {
          this.publicToken = null;
          this.tokenInfo = null;
          this.isPublicMode = false;
          this.showInvalidateConfirm = false;
          this.$emit("public-token-invalidated", { refcode: this.refcode });
        } else if (response.status === 403) {
          throw new Error("Only administrators can delete public tokens.");
        } else {
          throw new Error(data.detail || data.message || "Failed to invalidate token");
        }
      } catch (error) {
        console.error("Error invalidating token:", error);
        this.errorMessage = `Failed to invalidate token: ${error.message}`;
      } finally {
        this.isInvalidating = false;
      }
    },
  },
};
</script>

<style scoped>
.qrcode-text-label {
  font-family: var(--font-monospace);
  font-size: 1.8rem;
}

.shareable-link {
  border: 1px solid #dee2e6;
  border-radius: 0.25rem;
  padding: 0.375rem 0.75rem;
  background-color: #f8f9fa;
  width: 85%;
  margin-left: auto;
  margin-right: auto;
}

.shareable-link a {
  min-width: 0;
}

.label-printing {
  border-top: 1px solid #dee2e6;
  padding-top: 1rem;
}

.label-preview {
  border: 1px solid #adb5bd;
  background: white;
  color: black;
  font: 8px/1.2 monospace;
  overflow: hidden;
}

.label-preview img {
  display: block;
}
</style>
