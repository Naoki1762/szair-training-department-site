import { createApp } from "vue";

const host = document.createElement("div");
host.id = "training-vue-root";
host.hidden = true;
document.body.appendChild(host);

createApp({
  name: "TrainingPortalFrontend",
  data() {
    return {
      mountedAt: new Date().toISOString()
    };
  },
  template: "<span aria-hidden=\"true\"></span>"
}).mount(host);
