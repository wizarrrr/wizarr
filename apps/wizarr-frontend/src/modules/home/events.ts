import mitt from 'mitt';
import type { EventRecords } from './types/EventRecords';

const eventBus = mitt<EventRecords>();

export default eventBus;
