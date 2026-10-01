import "@testing-library/jest-dom";

const NativeFormData = globalThis.FormData;

class FormDataWithFileInputs extends NativeFormData {
	constructor(form) {
		super(form);
		if (form instanceof HTMLFormElement) {
			for (const input of form.querySelectorAll('input[type="file"]')) {
				if (input.files?.length) this.set(input.name, input.files[0]);
			}
		}
	}
}

globalThis.FormData = FormDataWithFileInputs;
window.FormData = FormDataWithFileInputs;