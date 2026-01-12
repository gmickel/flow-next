export interface Theme {
	name: string;
	colors: {
		primary: string;
		secondary: string;
		background: string;
		text: string;
		success: string;
		warning: string;
		error: string;
	};
}

export { darkTheme } from "./dark.ts";
export { lightTheme } from "./light.ts";
