<template>
    <div class="space-y-4 md:space-y-6">
        <div class="flex justify-center items-center py-4 flex-col space-y-8">
            <i class="fa-solid fa-fingerprint text-gray-900 dark:text-gray-300 text-7xl"></i>
            <h1 class="text-gray-900 dark:text-white font-extralight text-xl text-center font-semibold">
                {{ __("Use your Fingerprint or Face Recognition to Verify your Identity") }}
            </h1>
            <p class="text-gray-900 dark:text-white font-light text-xs text-center">
                {{ __("Press the button below and follow your browser's steps to login") }}
            </p>
        </div>

        <div class="space-y-2">
            <button @click="$emit('mfaLogin')" class="w-full text-white bg-secondary hover:bg-secondary_hover focus:ring-4 focus:outline-none focus:ring-grey-300 font-medium rounded text-sm px-5 py-2.5 text-center">
                {{ __("Continue") }}
            </button>
            <div class="flex justify-center items-center">
                <button @click="$emit('passwordLogin')" class="text-primary text-sm font-medium">
                    {{ __("Login with Password") }}
                </button>
            </div>
        </div>
    </div>
</template>
