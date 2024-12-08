import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
import { command } from "vite-plugin-command";

export default defineConfig({
	plugins: [
		command({
			pattern: "scripts/**/*.html",
			run: "yarn generate",
		}),
		tailwindcss(),
	],
});
