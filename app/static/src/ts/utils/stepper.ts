import { nanoid } from 'nanoid';

import addToWindow from './addToWindow';

class StepperBuilder {

    private stepperID: string = nanoid();
    private stepper: HTMLElement;
    private steps: Array<string>;
    private activeStep: number;
    private domElement: HTMLElement | null = null;

    constructor(steps: Array<string>) {
        this.steps = steps;
        this.activeStep = 0;

        this.stepper = this.createStepper();
        this.createSteps();
    }

    public build(domElement: HTMLElement) {
        this.domElement = domElement;
        this.domElement.innerHTML = this.stepper.outerHTML;
    }

    public setActiveStep(step: number) {
        this.activeStep = step;
        this.updateActiveStep();
    }

    private updateActiveStep() {
        const stepper = document.getElementById(this.stepperID);

        if (stepper == null) {
            return;
        }

        const steps = stepper.querySelectorAll('li');

        steps.forEach((step, index) => {
            index += 1;

            if (this.activeStep === index) {
                step.classList.add('after:border-primary');
                step.classList.remove('after:border-gray-100', 'after:dark:border-gray-700');
                step.querySelector('span')?.classList.remove('bg-gray-100', 'dark:bg-gray-700');
                step.querySelector('span')?.classList.add('bg-primary');
            }

            if (this.activeStep > index) {
                step.classList.add('after:border-primary');
                step.classList.remove('after:border-gray-100', 'after:dark:border-gray-700');
                step.querySelector('span')?.classList.remove('bg-gray-100', 'dark:bg-gray-700');
                step.querySelector('span')?.classList.add('bg-primary');
            }

            if (this.activeStep < index) {
                step.classList.add('after:border-gray-100', 'after:dark:border-gray-700');
                step.classList.remove('after:border-primary');
                step.querySelector('span')?.classList.remove('bg-primary');
                step.querySelector('span')?.classList.add('bg-gray-100', 'dark:bg-gray-700');
            }
        });
    }

    private createStepper() {
        const ol = document.createElement('ol');
        ol.classList.add('flex', 'items-center', 'w-full', 'text-white');
        ol.id = this.stepperID;
        return ol;
    }

    private createSteps() {
        this.steps.forEach((step, index) => {
            this.createStep(step, index);
        });
    }

    private createStep(icon: string, index: number) {
        const li = document.createElement('li');
        li.classList.add('flex', 'items-center');

        if (index !== this.steps.length - 1) {
            li.style.transition = 'border-color 0.3s ease';
            li.classList.add('w-full', 'after:content-[""]', 'after:w-full', 'after:h-1', 'after:border-b', 'after:border-gray-100', 'after:dark:border-gray-700', 'after:border-4', 'after:inline-block');
        }

        const span = document.createElement('span');
        span.classList.add('flex', 'items-center', 'justify-center', 'w-10', 'h-10', 'bg-gray-100', 'rounded-full', 'lg:h-12', 'lg:w-12', 'dark:bg-gray-700', 'shrink-0');
        span.style.transition = 'background-color 0.3s ease';

        const i = document.createElement('i');
        i.classList.add('fas', icon);

        span.appendChild(i);
        li.appendChild(span);
        this.stepper.appendChild(li);
    }
}

class StepperController {

    private stepper: HTMLElement;
    private activeStep: number = 0;

    constructor(stepper: HTMLElement | string) {
        const stepperElement = (typeof stepper === 'string') ? document.getElementById(stepper) : stepper;

        if (stepperElement == null) {
            throw new Error('Stepper not found');
        }

        this.stepper = stepperElement;
    }

    public setActiveStep(step: number) {
        this.activeStep = step;
        this.updateActiveStep();
    }

    private updateActiveStep() {
        const steps = this.stepper.querySelectorAll('li');

        steps.forEach((step, index) => {
            index += 1;

            if (this.activeStep === index) {
                step.classList.add('after:border-primary');
                step.classList.remove('after:border-gray-100', 'after:dark:border-gray-700');
                step.querySelector('span')?.classList.remove('bg-gray-100', 'dark:bg-gray-700');
                step.querySelector('span')?.classList.add('bg-primary');
            }

            if (this.activeStep > index) {
                step.classList.add('after:border-primary');
                step.classList.remove('after:border-gray-100', 'after:dark:border-gray-700');
                step.querySelector('span')?.classList.remove('bg-gray-100', 'dark:bg-gray-700');
                step.querySelector('span')?.classList.add('bg-primary');
            }

            if (this.activeStep < index) {
                step.classList.add('after:border-gray-100', 'after:dark:border-gray-700');
                step.classList.remove('after:border-primary');
                step.querySelector('span')?.classList.remove('bg-primary');
                step.querySelector('span')?.classList.add('bg-gray-100', 'dark:bg-gray-700');
            }
        });
    }
}

addToWindow(['utils', 'stepper', 'StepperBuilder'], StepperBuilder);
addToWindow(['utils', 'stepper', 'StepperController'], StepperController);
