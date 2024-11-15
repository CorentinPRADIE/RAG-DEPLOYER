<template>
  <v-container style="height: 100vh" class="d-flex flex-column justify-space-between">
    <v-row>
      <v-col cols="12">
        <div ref="messagesContainer" id="messages-container">
          <div class="d-flex" v-for="(msg, index) in displayedMessages" :key="index">
            <span class="mr-4 text-h6">{{ msg.role === "assistant" ? "✨" : "🧑‍💻" }}</span>
            <v-card class="mb-4" :variant="msg.role === 'assistant' ? 'outlined' : 'flat'">
              <v-card-text><pre style="white-space: pre-wrap; word-wrap: break-word;">{{ msg.content }}</pre></v-card-text>
            </v-card>
          </div>

          <div v-if="isTyping" class="d-flex">
            <span class="mr-4 text-h6">✨</span>
            <v-card class="mb-4" variant="outlined">
              <v-card-text><pre style="white-space: pre-wrap; word-wrap: break-word;">...</pre></v-card-text>
            </v-card>
          </div>
        </div>
      </v-col>
    </v-row>

    <v-row class="flex-grow-0 align-center">
      <v-col cols="12" class="d-flex align-center">
        <v-textarea
          v-model="message"
          label="Entrez votre message"
          variant="outlined"
          @click:append="sendMessage"
          @keydown.enter.prevent="sendMessage"
          single-line
          rows="2"
          no-resize
          class="flex-grow-1"
        >
          <template v-slot:append>
            <v-col class="d-flex flex-column mr-2 compact-toggles">
              <v-switch
                v-model="requiresDocumentSearch"
                label="Recherche documentaire"
                inset
                class="compact-toggle"
                :class="requiresDocumentSearch ? 'switch-active' : 'switch-inactive'"
              ></v-switch>

              <v-switch
                v-model="showContext"
                label="Afficher le contexte"
                inset
                class="compact-toggle"
                :class="showContext ? 'switch-active' : 'switch-inactive'"
              ></v-switch>

              <v-switch
                v-model="showPerformance"
                label="Afficher le rapport de performance"
                inset
                class="compact-toggle"
                :class="showPerformance ? 'switch-active' : 'switch-inactive'"
              ></v-switch>
            </v-col>

            <v-btn @click="sendMessage" :disabled="asyncState.isLoading" icon="mdi-send" variant="plain"></v-btn>
            <v-btn @click="resetConversation" icon="mdi-refresh" variant="plain" title="Réinitialiser la conversation"></v-btn>
          </template>
        </v-textarea>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, watch, nextTick, reactive } from "vue";

const messagesContainer = ref(null);
const message = ref("");
const requiresDocumentSearch = ref(false);
const showContext = ref(false);
const showPerformance = ref(false); // New switch for performance reports
const isTyping = ref(false);

const rawMessages = ref([
  {
    role: "assistant",
    content: "Bonjour, je suis Amélie, votre assistante de recherche ! Je suis là pour vous aider à explorer et répondre à vos questions en utilisant vos documents. Activez la recherche documentaire si vous souhaitez inclure des extraits précis, ou posez simplement votre question pour un sujet plus général.",
    context: "",
    performance: "",
  }
]);
const displayedMessages = ref([...rawMessages.value]);
const asyncState = reactive({ isLoading: false, error: null });

function updateDisplayedMessages() {
  displayedMessages.value = rawMessages.value.map((msg) => {
    let updatedContent = msg.content;

    if (msg.role === "assistant") {
      if (showContext.value && msg.context) {
        updatedContent = `--- DEBUT CONTEXTE ---\n${msg.context}\n--- FIN CONTEXTE ---\n\n${updatedContent}`;
      }

      if (showPerformance.value && msg.performance) {
        updatedContent += `\n\n--- PERFORMANCE ---\n${msg.performance}`;
      }
    }

    return { ...msg, content: updatedContent };
  });
}

async function fetchBackendResponse() {
  asyncState.isLoading = true;
  isTyping.value = true;

  try {
    const question = rawMessages.value[rawMessages.value.length - 1].content;
    const requiresDocumentSearchValue = requiresDocumentSearch.value;

    const history = rawMessages.value
      .slice(0, -1)
      .map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));

    const response = await fetch("http://localhost:5000/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        requiresDocumentSearch: requiresDocumentSearchValue,
        history,
      }),
    });

    const responseData = await response.json();
    if (response.ok && responseData.answer) {
      // Format performance info with two decimal precision
      const retrievalTime = responseData.retrieval_time
        ? responseData.retrieval_time.toFixed(2)
        : "N/A";
      const generationTime = responseData.generation_time
        ? responseData.generation_time.toFixed(2)
        : "N/A";
      const totalTime = responseData.total_time
        ? responseData.total_time.toFixed(2)
        : "N/A";

      const performanceInfo = `
Temps de récupération : ${retrievalTime} s
Temps de génération : ${generationTime} s
Temps total : ${totalTime} s`;

      rawMessages.value.push({
        role: "assistant",
        content: responseData.answer,
        context: responseData.context,
        performance: performanceInfo,
      });
      updateDisplayedMessages();
    } else {
      throw new Error(responseData.error || "Error generating response");
    }
  } catch (error) {
    console.error("Error fetching backend response:", error);
  } finally {
    asyncState.isLoading = false;
    isTyping.value = false;
  }
}


async function sendMessage() {
  if (asyncState.isLoading) return;
  if (message.value.trim()) {
    const userInput = message.value;
    message.value = "";
    rawMessages.value.push({ role: "user", content: userInput });
    updateDisplayedMessages();
    await fetchBackendResponse();
  }
}

function resetConversation() {
  rawMessages.value = [
    {
      role: "assistant",
      content: "Bonjour, je suis Amélie, votre assistante de recherche ! Je suis là pour vous aider à explorer et répondre à vos questions en utilisant vos documents. Activez la recherche documentaire si vous souhaitez inclure des extraits précis, ou posez simplement votre question pour un sujet plus général.",
      context: "",
      performance: "",
    }
  ];
  updateDisplayedMessages();
}

watch(showContext, updateDisplayedMessages);
watch(showPerformance, updateDisplayedMessages);

watch(
  displayedMessages,
  () => {
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
      }
    });
  },
  { deep: true }
);
</script>

<style>
#messages-container {
  max-height: 80vh;
  overflow-y: auto;
}

#message-box {
  word-wrap: break-word;
  white-space: pre-wrap;
}

.compact-toggles .compact-toggle {
  padding-top: 2px !important;
  padding-bottom: 2px !important;
  margin-top: -6px;
  margin-bottom: -6px;
  font-size: 0.8em;
}

.switch-active .v-input--switch__track {
  background-color: green !important;
}

.switch-inactive .v-input--switch__track {
  background-color: red !important;
}
</style>
