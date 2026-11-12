<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
defineProps<{ title: string }>()
const emit = defineEmits<{ close: [] }>()
const dialog = ref<HTMLDialogElement>()
const previous = document.activeElement as HTMLElement | null
onMounted(() => dialog.value?.showModal())
onUnmounted(() => previous?.focus())
</script>
<template><dialog ref="dialog" aria-labelledby="dialog-title" @close="emit('close')"><div class="dialog-head"><h2 id="dialog-title">{{ title }}</h2><button class="close" aria-label="关闭弹窗" @click="dialog?.close()">×</button></div><div class="dialog-body"><slot /></div></dialog></template>
