
import { test as base } from './worker-db.fixture';

type WorkcellFixtures = {
    testMachineData: { id: string; name: string };
};

export const test = base.extend<WorkcellFixtures>({
    testMachineData: async ({}, use) => {
        const machineId = `test-machine-${Date.now()}`;
        const machineName = 'Test Liquid Handler';
        await use({ id: machineId, name: machineName });
    },
});

export { expect } from '@playwright/test';
